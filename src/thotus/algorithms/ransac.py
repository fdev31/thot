# Ransac & sgf algorithm taken from Horus
# https://github.com/bqlabs/horus

import math

import scipy.ndimage
import numpy as np

def sgf(u, s):
    if len(u) > 1:
        i = 0
        sigma = 2.0
        f = np.array([])
        segments = [s[_r] for _r in np.ma.clump_unmasked(np.ma.masked_equal(s, 0))]
        # Detect stripe segments
        for segment in segments:
            j = len(segment)
            # Apply gaussian filter
            fseg = scipy.ndimage.gaussian_filter(u[i:i + j], sigma=sigma)
            f = np.concatenate((f, fseg))
            i += j
        return f
    else:
        return u

def ransac(u, v):
    if len(u) > 1:
        data = np.vstack((v.ravel(), u.ravel())).T
        dr, thetar = _ransac(data, LinearLeastSquares2D(), 300, 2)
        # v = np.array(range(min(v), max(v)))
        u = (dr - v * math.sin(thetar)) / math.cos(thetar)
    return u

def _ransac(data, model_class, min_samples, threshold, max_trials=100):
    '''
    Fits a model to data with the RANSAC algorithm.
    :param data: numpy.ndarray
        data set to which the model is fitted, must be of shape NxD where
        N is the number of data points and D the dimensionality of the data
    :param model_class: object
        object with the following methods implemented:
         * fit(data): return the computed model
         * residuals(model, data): return residuals for each data point
         * is_degenerate(sample): return boolean value if sample choice is
            degenerate
        see LinearLeastSquares2D class for a sample implementation
    :param min_samples: int
        the minimum number of data points to fit a model
    :param threshold: int or float
        maximum distance for a data point to count as an inlier
    :param max_trials: int, optional
        maximum number of iterations for random sample selection, default 100
    :returns: tuple
        best model returned by model_class.fit, best inlier indices
    '''

    best_model = None
    best_inlier_num = 0
    best_inliers = None
    data_idx = np.arange(data.shape[0])
    for _ in range(max_trials):
        sample = data[np.random.randint(0, data.shape[0], 2)]
        if model_class.is_degenerate(sample):
            continue
        sample_model = model_class.fit(sample)
        sample_model_residua = model_class.residuals(sample_model, data)
        sample_model_inliers = data_idx[sample_model_residua < threshold]
        inlier_num = sample_model_inliers.shape[0]
        if inlier_num > best_inlier_num:
            best_inlier_num = inlier_num
            best_inliers = sample_model_inliers
    if best_inliers is not None:
        best_model = model_class.fit(data[best_inliers])
    return best_model


class LinearLeastSquares2D(object):
    '''
    2D linear least squares using the hesse normal form:
        d = x*sin(theta) + y*cos(theta)
    which allows you to have vertical lines.
    '''

    def fit(self, data):
        data_mean = data.mean(axis=0)
        x0, y0 = data_mean
        if data.shape[0] > 2:  # over determined
            u, v, w = np.linalg.svd(data - data_mean)
            vec = w[0]
            theta = math.atan2(vec[0], vec[1])
        elif data.shape[0] == 2:  # well determined
            theta = math.atan2(data[1, 0] - data[0, 0], data[1, 1] - data[0, 1])
        theta = (theta + math.pi * 5 / 2) % (2 * math.pi)
        d = x0 * math.sin(theta) + y0 * math.cos(theta)
        return d, theta

    def residuals(self, model, data):
        d, theta = model
        dfit = data[:, 0] * math.sin(theta) + data[:, 1] * math.cos(theta)
        return np.abs(d - dfit)

    def is_degenerate(self, sample):
        return False
