from thotus.algorithms.utils import compute_line_image
from thotus.algorithms.ransac import ransac
from thotus import settings
from thotus import imtools
import numpy as np
import cv2

def find_nearest(array,value):
    idx = (np.abs(array-value)).argmin()
    return array[idx]

def find_nearest(a, a0):
    "Element in nd array `a` closest to the scalar value `a0`"
    idx = np.abs(a - a0).argmin()
    return a.flat[idx]

def compute(img, img_g, ref, ref_g, laser_nr, mask=None, threshold=None, use_ransac=False):
    x = []
    y = []
    threshold = threshold if threshold is not None else settings.algo_threshold
    denoise = settings.algo_denoise

    bound = 0 if laser_nr == 0 else -1

    img = imtools.subtract(img_g, ref_g, mask=mask, blur=(3, 3))
    mask = imtools.compute_noise_mask(img, power=denoise, threshold=threshold)
    img = imtools.mask_contours(img, mask=mask)

    mid = img.shape[1]/2

    for n in range(img.shape[0]):
        max_val = np.max(img[n])
        if max_val > 1:
            peaks = np.where(img[n] == max_val)[0]
            y.append(n)
            x.append(find_nearest(peaks, mid))

    y = np.array(y)
    x = np.array(x)

    if use_ransac:  # line calibration
        x = ransac( x, y )

    points = (x, y)
    if points:
        return (points, compute_line_image(points, img))
    return None, None

