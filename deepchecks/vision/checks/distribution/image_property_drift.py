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
"""Module contains Image Property Drift check."""
import typing as t
from collections import defaultdict

import pandas as pd
from deepchecks.utils.distribution.drift import calc_drift_and_plot
from deepchecks.core import DatasetKind
from deepchecks.core import CheckResult
from deepchecks.core import ConditionResult
from deepchecks.vision import TrainTestCheck
from deepchecks.vision import Context
from deepchecks.vision import Batch
from deepchecks.vision.utils import image_properties


__all__ = ['ImagePropertyDrift']


TImagePropertyDrift = t.TypeVar('TImagePropertyDrift', bound='ImagePropertyDrift')


class ImagePropertyDrift(TrainTestCheck):
    """
    Calculate drift between train dataset and test dataset per image property, using statistical measures.

    Check calculates a drift score for each image property in test dataset, by comparing its distribution to the train
    dataset. For this, we use the Earth Movers Distance.

    See https://en.wikipedia.org/wiki/Wasserstein_metric

    Parameters
    ----------
    alternative_image_properties : List[Dict[str, Any]], default: None
        List of properties. Replaces the default deepchecks properties.
        Each property is dictionary with keys 'name' (str), 'method' (Callable) and 'output_type' (str),
        representing attributes of said method. 'output_type' must be one of 'continuous'/'discrete'
    max_num_categories: int, default: 10
    """

    def __init__(
        self,
        alternative_image_properties: t.List[t.Dict[str, t.Any]] = None,
        max_num_categories: int = 10
    ):
        super().__init__()
        if alternative_image_properties is not None:
            image_properties.validate_properties(alternative_image_properties)
            self.image_properties = alternative_image_properties
        else:
            self.image_properties = image_properties.default_image_properties

        self.max_num_categories = max_num_categories
        self.train_properties = defaultdict(list)
        self.test_properties = defaultdict(list)

    def update(
        self,
        context: Context,
        batch: Batch,
        dataset_kind: DatasetKind
    ):
        """Calculate image properties for train or test batch."""
        if dataset_kind == DatasetKind.TRAIN:
            properties = self.train_properties
        elif dataset_kind == DatasetKind.TEST:
            properties = self.test_properties
        else:
            raise RuntimeError(
                f'Internal Error - Should not reach here! unknown dataset_kind: {dataset_kind}'
            )

        images = batch.images

        for single_property in self.image_properties:
            properties[single_property['name']].extend(single_property['method'](images))

    def compute(self, context: Context) -> CheckResult:
        """Calculate drift score between train and test datasets for the collected image properties.

        Returns
        -------
        CheckResult
            value: dictionary containing drift score for each image property.
            display: distribution graph for each image property.
        """
        if sorted(self.train_properties.keys()) != sorted(self.test_properties.keys()):
            raise RuntimeError('Internal Error! Vision check was used improperly.')

        properties = sorted(self.train_properties.keys())
        df_train = pd.DataFrame(self.train_properties)
        df_test = pd.DataFrame(self.test_properties)

        figures = {}
        drifts = {}

        for single_property in self.image_properties:
            property_name = single_property['name']

            score, _, figure = calc_drift_and_plot(
                train_column=df_train[property_name],
                test_column=df_test[property_name],
                plot_title=property_name,
                column_type=image_properties.get_column_type(single_property['output_type']),
                max_num_categories=self.max_num_categories
            )

            figures[property_name] = figure
            drifts[property_name] = score

        if drifts:
            columns_order = sorted(properties, key=lambda col: drifts[col], reverse=True)

            headnote = '<span>' \
                       'The Drift score is a measure for the difference between two distributions. ' \
                       'In this check, drift is measured ' \
                       f'for the distribution of the following image properties: {properties}.' \
                       '</span>'

            displays = [headnote] + [figures[col] for col in columns_order]
        else:
            drifts = None
            displays = []

        return CheckResult(
            value=drifts,
            display=displays,
            header='Image Property Drift'
        )

    def add_condition_drift_score_not_greater_than(
        self: TImagePropertyDrift,
        max_allowed_drift_score: float = 0.1
    ) -> TImagePropertyDrift:
        """
        Add condition - require drift score to not be more than a certain threshold.

        Parameters
        ----------
        max_allowed_drift_score: float ,  default: 0.1
            the max threshold for the Earth Mover's Distance score

        Returns
        -------
        ConditionResult
            False if any column has passed the max threshold, True otherwise
        """

        def condition(result: t.Dict[str, float]) -> ConditionResult:
            failed_properties = [
                (property_name, drift_score)
                for property_name, drift_score in result.items()
                if drift_score > max_allowed_drift_score
            ]
            if len(failed_properties) > 0:
                failed_properties = ';\n'.join(f'{p}={d:.2f}' for p, d in failed_properties)
                return ConditionResult(
                    False,
                    'Earth Mover\'s Distance is above the threshold '
                    f'for the next properties:\n{failed_properties}'
                )
            return ConditionResult(True)

        return self.add_condition(
            f'Earth Mover\'s Distance <= {max_allowed_drift_score} for image properties drift',
            condition
        )
