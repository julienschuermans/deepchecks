"""Contains unit tests for the Dataset class."""
import pandas as pd

from mlchecks import Dataset, ensure_dataframe_type
from mlchecks.utils import MLChecksValueError
from hamcrest import assert_that, instance_of, equal_to, is_, calling, raises, not_none


def assert_dataset(dataset: Dataset, args):
    assert_that(dataset, instance_of(Dataset))
    if 'df' in args:
        assert_that(dataset.data.equals(args['df']), is_(True))
    if 'features' in args:
        assert_that(dataset.features(), equal_to(args['features']))
        if 'df' in args:
            assert_that(dataset.features_columns().equals(args['df'][args['features']]), is_(True))
    if 'cat_features' in args:
        assert_that(dataset.cat_features(), equal_to(args['cat_features']))
    if 'label' in args:
        assert_that(dataset.label_name(), equal_to(args['label']))
        assert_that(dataset.label_col().equals(pd.Series(args['df'][args['label']])), is_(True))
    if 'use_index' in args and args['use_index']:
        assert_that(dataset.index_col().equals(pd.Series(args['df'].index)), is_(True))
    if 'index' in args:
        assert_that(dataset.index_name(), equal_to(args['index']))
        assert_that(dataset.index_col().equals(pd.Series(args['df'][args['index']])), is_(True))
    if 'date' in args:
        assert_that(dataset.date_name(), equal_to(args['date']))
        if ('_convert_date' in args) and (args['_convert_date'] is False):
            assert_that(dataset.date_col().equals(pd.Series(args['df'][args['date']])), is_(True))
        else:
            for date in dataset.date_col():
                assert_that(date, instance_of(pd.Timestamp))


def test_dataset_empty_df(empty_df):
    args = {'df': empty_df}
    dataset = Dataset(**args)
    assert_dataset(dataset, args)


def test_dataset_feature_columns(iris):
    args = {'df': iris,
            'features': ['sepal length (cm)',
                         'sepal width (cm)',
                         'petal length (cm)',
                         'petal width (cm)']}
    dataset = Dataset(**args)
    assert_dataset(dataset, args)


def test_dataset_less_features(iris):
    args = {'df': iris,
            'features': ['sepal length (cm)',
                         'sepal width (cm)',
                         'petal length (cm)']}
    dataset = Dataset(**args)
    assert_dataset(dataset, args)


def test_dataset_bad_feature(iris):
    args = {'df': iris,
            'features': ['sepal length - no exists']}
    assert_that(calling(Dataset).with_args(**args),
                raises(MLChecksValueError, 'Features must be names of columns in dataframe. Features '
                                           '{\'sepal length - no exists\'} have not been found in input dataframe.'))


def test_dataset_empty_features(iris):
    args = {'df': iris,
            'features': []}
    dataset = Dataset(**args)
    assert_that(dataset.features(), equal_to(list(iris.columns)))


def test_dataset_cat_features(diabetes_df):
    args = {'df': diabetes_df,
            'cat_features': ['sex']}
    dataset = Dataset(**args)
    assert_dataset(dataset, args)


def test_dataset_bad_cat_feature(diabetes_df):
    args = {'df': diabetes_df,
            'cat_features': ['something else']}
    assert_that(calling(Dataset).with_args(**args),
                raises(MLChecksValueError, 'Categorical features must be a subset of features. '
                                           'Categorical features {\'something else\'} '
                                           'have not been found in feature list.'))


def test_dataset_cat_feature_not_in_features(diabetes_df):
    args = {'df': diabetes_df,
            'features': ['age',
                         'bmi',
                         'bp',
                         's1',
                         's2',
                         's3',
                         's4',
                         's5',
                         's6'],
            'cat_features': ['sex']}
    assert_that(calling(Dataset).with_args(**args),
                raises(MLChecksValueError, 'Categorical features must be a subset of features. '
                                           'Categorical features {\'sex\'} '
                                           'have not been found in feature list.'))


def test_dataset_infer_cat_features(diabetes_df):
    args = {'df': diabetes_df,
            'features': ['age',
                         'bmi',
                         'sex',
                         'bp',
                         's1',
                         's2',
                         's3',
                         's4',
                         's5',
                         's6']}

    dataset = Dataset(**args)
    args['cat_features'] = ['age', 'sex', 'bp', 's3', 's4', 's6']
    assert_dataset(dataset, args)


def test_dataset_infer_cat_features_max_categoreis(diabetes_df):
    args = {'df': diabetes_df,
            'features': ['age',
                         'bmi',
                         'sex',
                         'bp',
                         's1',
                         's2',
                         's3',
                         's4',
                         's5',
                         's6'],
            'max_categories': 10}

    dataset = Dataset(**args)
    args['cat_features'] = ['sex']
    assert_dataset(dataset, args)


def test_dataset_infer_cat_features_max_categorical_ratio(diabetes_df):
    args = {'df': diabetes_df,
            'features': ['age',
                         'bmi',
                         'sex',
                         'bp',
                         's1',
                         's2',
                         's3',
                         's4',
                         's5',
                         's6'],
            'max_categories': 10,
            'max_categorical_ratio': 0.13}

    dataset = Dataset(**args)
    args['cat_features'] = ['sex', 's6']
    assert_dataset(dataset, args)


def test_dataset_label(iris):
    args = {'df': iris,
            'label': 'target'}
    dataset = Dataset(**args)
    assert_dataset(dataset, args)


def test_dataset_label_in_features(iris):
    args = {'df': iris,
            'features': ['sepal length (cm)',
                         'sepal width (cm)',
                         'petal length (cm)',
                         'petal width (cm)',
                         'target'],
            'label': 'target'}
    assert_that(calling(Dataset).with_args(**args),
                raises(MLChecksValueError, 'label column target can not be a feature column'))


def test_dataset_bad_label(iris):
    args = {'df': iris,
            'label': 'shmabel'}
    assert_that(calling(Dataset).with_args(**args),
                raises(MLChecksValueError, 'label column shmabel not found in dataset columns'))


def test_dataset_use_index(iris):
    args = {'df': iris,
            'use_index': True}
    dataset = Dataset(**args)
    assert_dataset(dataset, args)


def test_dataset_index_use_index(iris):
    args = {'df': iris,
            'index': 'target',
            'use_index': True}
    assert_that(calling(Dataset).with_args(**args),
                raises(MLChecksValueError, 'parameter use_index cannot be True if index is given'))


def test_dataset_index_from_column(iris):
    args = {'df': iris,
            'index': 'target'}
    dataset = Dataset(**args)
    assert_dataset(dataset, args)


def test_dataset_index_in_df(iris):
    args = {'df': iris,
            'features': ['sepal length (cm)',
                         'sepal width (cm)',
                         'petal length (cm)',
                         'petal width (cm)'],
            'index': 'index'}
    assert_that(calling(Dataset).with_args(**args),
                raises(MLChecksValueError, 'index column index not found in dataset columns. If you attempted to use '
                                           'the dataframe index, set use_index to True instead.'))


def test_dataset_index_in_features(iris):
    args = {'df': iris,
            'features': ['sepal length (cm)',
                         'sepal width (cm)',
                         'petal length (cm)',
                         'petal width (cm)',
                         'target'],
            'index': 'target'}
    assert_that(calling(Dataset).with_args(**args),
                raises(MLChecksValueError, 'index column target can not be a feature column'))


def test_dataset_date(iris):
    args = {'date': 'target'}
    dataset = Dataset(iris, **args)
    assert_dataset(dataset, args)


def test_dataset_date_not_in_columns(iris):
    args = {'date': 'date'}
    assert_that(calling(Dataset).with_args(iris, **args),
                raises(MLChecksValueError, 'date column date not found in dataset columns'))


def test_dataset_date_in_features(iris):
    args = {'df': iris,
            'features': ['sepal length (cm)',
                         'sepal width (cm)',
                         'petal length (cm)',
                         'petal width (cm)',
                         'target'],
            'date': 'target'}
    assert_that(calling(Dataset).with_args(**args),
                raises(MLChecksValueError, 'date column target can not be a feature column'))


def test_dataset_date_unit_type():
    df = pd.DataFrame({'date': [1, 2]})
    args = {'date': 'date',
            'date_unit_type': 'D'}
    dataset = Dataset(df, **args)
    assert_dataset(dataset, args)
    date_col = dataset.date_col()
    assert_that(date_col, not_none())
    # disable false positive
    # pylint:disable=unsubscriptable-object
    assert_that(date_col[0], is_(pd.Timestamp(1, unit='D')))
    assert_that(date_col[1], is_(pd.Timestamp(2, unit='D')))


def test_dataset_date_convert_date():
    df = pd.DataFrame({'date': [1, 2]})
    args = {'df': df,
            'date': 'date',
            '_convert_date': False}
    dataset = Dataset(**args)
    assert_dataset(dataset, args)
    date_col = dataset.date_col()
    assert_that(date_col, not_none())
    # disable false positive
    # pylint:disable=unsubscriptable-object
    assert_that(date_col[0], is_(1))
    assert_that(date_col[1], is_(2))


def test_dataset_data(iris):
    dataset = Dataset(iris)
    iris.equals(dataset.data)


def test_dataset_n_samples(iris):
    dataset = Dataset(iris)
    assert_that(dataset.n_samples(), is_(iris.shape[0]))


def test_dataset_no_index_col(iris):
    dataset = Dataset(iris)
    assert_that(dataset.index_col(), is_(None))


def test_dataset_validate_label(iris):
    dataset = Dataset(iris, label='target')
    dataset.validate_label('test')


def test_dataset_validate_no_label(iris):
    dataset = Dataset(iris)
    assert_that(calling(dataset.validate_label).with_args('test'),
                raises(MLChecksValueError, 'function test requires dataset to have a label column'))


def test_dataset_validate_date(iris):
    dataset = Dataset(iris, date='target')
    dataset.validate_date('test')


def test_dataset_validate_no_date(iris):
    dataset = Dataset(iris)
    assert_that(calling(dataset.validate_date).with_args('test'),
                raises(MLChecksValueError, 'function test requires dataset to have a date column'))


def test_dataset_validate_index(iris):
    dataset = Dataset(iris, index='target')
    dataset.validate_index('test')


def test_dataset_validate_no_index(iris):
    dataset = Dataset(iris)
    assert_that(calling(dataset.validate_index).with_args('test'),
                raises(MLChecksValueError, 'function test requires dataset to have an index column'))


def test_dataset_filter_columns_with_validation(iris):
    dataset = Dataset(iris)
    filtered = dataset.filter_columns_with_validation(columns=['target'])
    assert_that(filtered, instance_of(Dataset))


def test_dataset_filter_columns_with_validation_ignore_columns(iris):
    dataset = Dataset(iris)
    filtered = dataset.filter_columns_with_validation(ignore_columns=['target'])
    assert_that(filtered, instance_of(Dataset))


def test_dataset_filter_columns_with_validation_same_table(iris):
    dataset = Dataset(iris, features=['target'])
    filtered = dataset.filter_columns_with_validation(ignore_columns=['target'])
    assert_that(filtered, instance_of(Dataset))


def test_dataset_validate_shared_features(diabetes):
    train, val = diabetes
    assert_that(train.validate_shared_features(val, 'test'), is_(val.features()))


def test_dataset_validate_shared_features_fail(diabetes, iris_dataset):
    train = diabetes[0]
    assert_that(calling(train.validate_shared_features).with_args(iris_dataset, 'test'),
                raises(MLChecksValueError, 'function test requires datasets to share the same features'))


def test_dataset_validate_shared_label(diabetes):
    train, val = diabetes
    assert_that(train.validate_shared_label(val, 'test'), is_(val.label_name()))


def test_dataset_validate_shared_labels_fail(diabetes, iris_dataset):
    train = diabetes[0]
    assert_that(calling(train.validate_shared_label).with_args(iris_dataset, 'test'),
                raises(MLChecksValueError, 'function test requires datasets to share the same label'))


def test_dataset_shared_categorical_features(diabetes_df, iris):
    diabetes_dataset = Dataset(diabetes_df)
    iris_dataset = Dataset(iris)
    assert_that(calling(diabetes_dataset.validate_shared_categorical_features).with_args(iris_dataset, 'test'),
                raises(MLChecksValueError, 'function test requires datasets to share'
                                           ' the same categorical features'))


def test_validate_dataset_or_dataframe_empty_df(empty_df):
    assert_that(calling(Dataset.validate_dataset_or_dataframe).with_args(empty_df),
                raises(MLChecksValueError, 'dataset cannot be empty'))


def test_validate_dataset_or_dataframe_empty_dataset(empty_df):
    assert_that(calling(Dataset.validate_dataset_or_dataframe).with_args(Dataset(empty_df)),
                raises(MLChecksValueError, 'dataset cannot be empty'))


def test_validate_dataset_or_dataframe(iris):
    assert_that(Dataset.validate_dataset_or_dataframe(iris), Dataset(iris))


def test_validate_dataset_empty_df(empty_df):
    assert_that(calling(Dataset.validate_dataset).with_args(Dataset(empty_df), 'test_function'),
                raises(MLChecksValueError, 'function test_function required a non-empty dataset'))


def test_validate_dataset_not_dataset():
    assert_that(calling(Dataset.validate_dataset).with_args('not_dataset', 'test_function'),
                raises(MLChecksValueError, 'function test_function requires dataset to be of type Dataset. instead got:'
                                           ' str'))


def test_ensure_dataframe_type(iris):
    assert_that(ensure_dataframe_type(iris).equals(iris), is_(True))


def test_ensure_dataframe_type_dataset(iris):
    assert_that(ensure_dataframe_type(Dataset(iris)).equals(iris), is_(True))


def test_ensure_dataframe_type_fail():
    assert_that(calling(ensure_dataframe_type).with_args('not dataset'),
                raises(MLChecksValueError, 'dataset must be of type DataFrame or Dataset, but got: str'))