# ----------------------------------------------------------------------------
# Copyright (C) 2021-2022 Deepchecks (https://www.deepchecks.com)
#
# This file is part of Deepchecks.
# Deepchecks is distributed under the terms of the GNU Affero General
# Public License (version 3 or later).
# You should have received a copy of the GNU Affero General Public License
# along with Deepchecks.  If not, see <http://www.gnu.org/licenses/>.
# ----------------------------------------------------------------------------
#
"""Module contains Train Test Prediction Drift check."""
from typing import Dict, List, Any
from collections import OrderedDict, defaultdict

import pandas as pd

from deepchecks import ConditionResult
from deepchecks.utils.distribution.drift import calc_drift_and_plot
from deepchecks.core import DatasetKind, CheckResult
from deepchecks.core.errors import DeepchecksNotSupportedError
from deepchecks.vision import Context, TrainTestCheck, Batch
from deepchecks.vision.vision_data import TaskType
from deepchecks.vision.utils.label_prediction_properties import validate_properties, \
    DEFAULT_CLASSIFICATION_PREDICTION_PROPERTIES, DEFAULT_OBJECT_DETECTION_PREDICTION_PROPERTIES, get_column_type

__all__ = ['TrainTestPredictionDrift']


class TrainTestPredictionDrift(TrainTestCheck):
    """
    Calculate prediction drift between train dataset and test dataset, using statistical measures.

    Check calculates a drift score for the predictions in the test dataset, by comparing its distribution to the
    train dataset. As the predictions may be complex, we calculate different properties of the predictions and check
    their distribution.

    A prediction property is any function that gets predictions and returns list of values. each
    value represents a property of the prediction, such as number of objects in image or tilt of each bounding box
    in image.

    There are default properties per task:
    For classification:
    - distribution of classes

    For object detection:
    - distribution of classes
    - distribution of bounding box areas
    - distribution of number of bounding boxes per image

    For numerical distributions, we use the Earth Movers Distance.
    See https://en.wikipedia.org/wiki/Wasserstein_metric
    For categorical distributions, we use the Population Stability Index (PSI).
    See https://www.lexjansen.com/wuss/2017/47_Final_Paper_PDF.pdf.


    Parameters
    ----------
    alternative_prediction_properties : List[Dict[str, Any]], default: None
        List of properties. Replaces the default deepchecks properties.
        Each property is dictionary with keys 'name' (str), 'method' (Callable) and 'output_type' (str),
        representing attributes of said method. 'output_type' must be one of 'continuous'/'discrete'/'class_id'
    max_num_categories : int , default: 10
        Only for non-continues properties. Max number of allowed categories. If there are more,
        they are binned into an "Other" category. If max_num_categories=None, there is no limit. This limit applies
        for both drift calculation and for distribution plots.
    """

    def __init__(
            self,
            alternative_prediction_properties: List[Dict[str, Any]] = None,
            max_num_categories: int = 10
    ):
        super().__init__()
        # validate alternative_prediction_properties:
        if alternative_prediction_properties is not None:
            validate_properties(alternative_prediction_properties)
        self.alternative_prediction_properties = alternative_prediction_properties
        self.max_num_categories = max_num_categories
        self._prediction_properties = None
        self._train_prediction_properties = None
        self._test_prediction_properties = None

    def initialize_run(self, context: Context):
        """Initialize run.

        Function initializes the following private variables:

        Prediction properties:
        _prediction_properties: all predictions properties to be calculated in run

        Prediction properties caching: _train_prediction_properties, _test_prediction_properties: Dicts of lists
        accumulating the predictions properties computed for each batch.
        """
        train_dataset = context.train

        task_type = train_dataset.task_type

        if self.alternative_prediction_properties is not None:
            self._prediction_properties = self.alternative_prediction_properties
        elif task_type == TaskType.CLASSIFICATION:
            self._prediction_properties = DEFAULT_CLASSIFICATION_PREDICTION_PROPERTIES
        elif task_type == TaskType.OBJECT_DETECTION:
            self._prediction_properties = DEFAULT_OBJECT_DETECTION_PREDICTION_PROPERTIES
        else:
            raise NotImplementedError('TrainTestLabelDrift must receive either alternative_prediction_properties or '
                                      'run on Classification or Object Detection class')

        self._train_prediction_properties = defaultdict(list)
        self._test_prediction_properties = defaultdict(list)

    def update(self, context: Context, batch: Batch, dataset_kind):
        """Perform update on batch for train or test properties."""
        # For all transformers, calculate histograms by batch:
        if dataset_kind == DatasetKind.TRAIN:
            properties = self._train_prediction_properties
        elif dataset_kind == DatasetKind.TEST:
            properties = self._test_prediction_properties
        else:
            raise DeepchecksNotSupportedError(f'Unsupported dataset kind {dataset_kind}')

        for prediction_property in self._prediction_properties:
            properties[prediction_property['name']] += prediction_property['method'](batch.predictions)

    def compute(self, context: Context) -> CheckResult:
        """Calculate drift on prediction properties samples that were collected during update() calls.

        Returns
        -------
        CheckResult
            value: drift score.
            display: label distribution graph, comparing the train and test distributions.
        """
        values_dict = OrderedDict()
        displays_dict = OrderedDict()
        prediction_properties_names = [x['name'] for x in self._prediction_properties]
        for prediction_property in self._prediction_properties:
            name = prediction_property['name']
            output_type = prediction_property['output_type']
            # If type is class converts to label names
            if output_type == 'class_id':
                self._train_prediction_properties[name] = [context.train.label_id_to_name(class_id) for class_id in
                                                           self._train_prediction_properties[name]]
                self._test_prediction_properties[name] = [context.test.label_id_to_name(class_id) for class_id in
                                                          self._test_prediction_properties[name]]

            value, method, display = calc_drift_and_plot(
                train_column=pd.Series(self._train_prediction_properties[name]),
                test_column=pd.Series(self._test_prediction_properties[name]),
                plot_title=name,
                column_type=get_column_type(output_type),
                max_num_categories=self.max_num_categories
            )
            values_dict[name] = {
                'Drift score': value,
                'Method': method,
            }
            displays_dict[name] = display

        columns_order = sorted(prediction_properties_names, key=lambda col: values_dict[col]['Drift score'],
                               reverse=True)

        headnote = '<span>' \
                   'The Drift score is a measure for the difference between two distributions. ' \
                   'In this check, drift is measured ' \
                   f'for the distribution of the following prediction properties: {prediction_properties_names}.' \
                   '</span>'

        displays = [headnote] + [displays_dict[col] for col in columns_order]

        return CheckResult(value=values_dict, display=displays, header='Train Test Prediction Drift')

    def add_condition_drift_score_not_greater_than(self, max_allowed_psi_score: float = 0.15,
                                                   max_allowed_earth_movers_score: float = 0.075
                                                   ) -> 'TrainTestPredictionDrift':
        """
        Add condition - require prediction properties drift score to not be more than a certain threshold.

        The industry standard for PSI limit is above 0.2.
        Earth movers does not have a common industry standard.
        The threshold was lowered by 25% compared to feature drift defaults due to the higher importance of prediction
        drift.

        Parameters
        ----------
        max_allowed_psi_score: float , default: 0.15
            the max threshold for the PSI score
        max_allowed_earth_movers_score: float , default: 0.075
            the max threshold for the Earth Mover's Distance score
        Returns
        -------
        ConditionResult
            False if any property has passed the max threshold, True otherwise
        """

        def condition(result: Dict) -> ConditionResult:
            not_passing_categorical_columns = {props: f'{d["Drift score"]:.2}' for props, d in result.items() if
                                               d['Drift score'] > max_allowed_psi_score and d['Method'] == 'PSI'}
            not_passing_numeric_columns = {props: f'{d["Drift score"]:.2}' for props, d in result.items() if
                                           d['Drift score'] > max_allowed_earth_movers_score
                                           and d['Method'] == "Earth Mover's Distance"}
            return_str = ''
            if not_passing_categorical_columns:
                return_str += f'Found non-continues prediction properties with PSI drift score above threshold:' \
                              f' {not_passing_categorical_columns}\n'
            if not_passing_numeric_columns:
                return_str += f'Found continues prediction properties with Earth Mover\'s drift score above' \
                              f' threshold: {not_passing_numeric_columns}\n'

            if return_str:
                return ConditionResult(False, return_str)
            else:
                return ConditionResult(True)

        return self.add_condition(f'PSI <= {max_allowed_psi_score} and Earth Mover\'s Distance <= '
                                  f'{max_allowed_earth_movers_score} for prediction drift',
                                  condition)
