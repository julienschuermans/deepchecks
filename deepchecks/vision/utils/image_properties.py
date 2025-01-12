# ----------------------------------------------------------------------------
# Copyright (C) 2021 Deepchecks (https://www.deepchecks.com)
#
# This file is part of Deepchecks.
# Deepchecks is distributed under the terms of the GNU Affero General
# Public License (version 3 or later).
# You should have received a copy of the GNU Affero General Public License
# along with Deepchecks.  If not, see <http://www.gnu.org/licenses/>.
# ----------------------------------------------------------------------------
#
"""Module containing the image formatter class for the vision module."""
from typing import Tuple, List

import numpy as np
from skimage.color import rgb2gray

from deepchecks.core.errors import DeepchecksValueError

__all__ = ['default_image_properties',
           'aspect_ratio',
           'area',
           'brightness',
           'rms_contrast',
           'normalized_red_mean',
           'normalized_blue_mean',
           'normalized_green_mean',
           'get_size',
           'get_dimension',
           'validate_properties',
           'get_column_type']


def aspect_ratio(batch: List[np.ndarray]) -> List[float]:
    """Return list of floats of image height to width ratio."""
    return [x[0] / x[1] for x in _sizes(batch)]


def area(batch: List[np.ndarray]) -> List[int]:
    """Return list of integers of image areas (height multiplied by width)."""
    return [np.prod(get_size(img)) for img in batch]


def brightness(batch: List[np.ndarray]) -> List[float]:
    """Calculate brightness on each image in the batch."""
    if _is_grayscale(batch) is True:
        return [img.mean() for img in batch]
    else:
        return [rgb2gray(img).mean() for img in batch]


def rms_contrast(batch: List[np.array]) -> List[float]:
    """Return RMS contrast of image."""
    if _is_grayscale(batch) is False:
        batch = [rgb2gray(img) for img in batch]

    return [img.std() for img in batch]


def normalized_red_mean(batch: List[np.ndarray]) -> List[float]:
    """Return the normalized mean of the red channel."""
    return [x[0] for x in _normalized_rgb_mean(batch)]


def normalized_green_mean(batch: List[np.ndarray]) -> List[float]:
    """Return the normalized mean of the green channel."""
    return [x[1] for x in _normalized_rgb_mean(batch)]


def normalized_blue_mean(batch: List[np.ndarray]) -> List[float]:
    """Return the normalized mean of the blue channel."""
    return [x[2] for x in _normalized_rgb_mean(batch)]


def _sizes(batch: List[np.ndarray]):
    """Return list of tuples of image height and width."""
    return [get_size(img) for img in batch]


def _normalized_rgb_mean(batch: List[np.ndarray]) -> List[Tuple[float, float, float]]:
    """Calculate normalized mean for each channel (rgb) in image.

    The normalized mean of each channel is calculated by first normalizing the image's pixels (meaning, each color
    is normalized to its relevant intensity, by dividing the color intensity by the other colors). Then, the mean
    for each image channel is calculated.

    Parameters
    ----------
    batch: List[np.ndarray]
        A list of arrays, each arrays represents an image in the required deepchecks format.
    sample_size_for_image_properties: int
        The number of pixels to sample from each image.

    Returns
    -------
    List[np.ndarray]:
        List of 3-dimensional arrays, each dimension is the normalized mean of the color channel. An array is
        returned for each image.
    """
    if _is_grayscale(batch) is True:
        return [(None, None, None)] * len(batch)

    return [_normalize_pixelwise(img).mean(axis=(1, 2)) for img in batch]


def _normalize_pixelwise(img: np.ndarray) -> np.ndarray:
    """Normalize the pixel values of an image.

    Parameters
    ----------
    img: np.ndarray
        The image to normalize.

    Returns
    -------
    np.ndarray
        The normalized image.
    """
    s = img.sum(axis=2)
    return np.array([np.divide(img[:, :, i], s, out=np.zeros_like(img[:, :, i], dtype='float64'), where=s != 0)
                     for i in range(3)])


def _is_grayscale(batch):
    return get_dimension(batch[0]) == 1


def get_size(img) -> Tuple[int, int]:
    """Get size of image as (height, width) tuple."""
    return img.shape[0], img.shape[1]


def get_dimension(img) -> int:
    """Return the number of dimensions of the image (grayscale = 1, RGB = 3)."""
    return img.shape[2]


default_image_properties = [
    {'name': 'Aspect Ratio', 'method': aspect_ratio, 'output_type': 'continuous'},
    {'name': 'Area', 'method': area, 'output_type': 'continuous'},
    {'name': 'Brightness', 'method': brightness, 'output_type': 'continuous'},
    {'name': 'RMS Contrast', 'method': rms_contrast, 'output_type': 'continuous'},
    {'name': 'Normalized Red Mean', 'method': normalized_red_mean, 'output_type': 'continuous'},
    {'name': 'Normalized Blue Mean', 'method': normalized_blue_mean, 'output_type': 'continuous'},
    {'name': 'Normalized Green Mean', 'method': normalized_green_mean, 'output_type': 'continuous'}
]


def validate_properties(properties):
    """Validate structure of measurements."""
    expected_keys = ['name', 'method', 'output_type']
    output_types = ['discrete', 'continuous']
    if not isinstance(properties, list):
        raise DeepchecksValueError(
            f'Expected properties to be a list, instead got {properties.__class__.__name__}')
    if len(properties) == 0:
        raise DeepchecksValueError('Properties list can\'t be empty')
    for label_property in properties:
        if not isinstance(label_property, dict) or any(
                key not in label_property.keys() for key in expected_keys):
            raise DeepchecksValueError(f'Property must be of type dict, and include keys {expected_keys}')
        if label_property['output_type'] not in output_types:
            raise DeepchecksValueError(f'Property field "output_type" must be one of {output_types}')


def get_column_type(output_type):
    """Get column type to use in drift functions."""
    # TODO smarter mapping based on data?
    mapper = {'continuous': 'numerical', 'discrete': 'categorical'}
    return mapper[output_type]
