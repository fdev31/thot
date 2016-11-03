import numpy as np
import cv2

from thotus.algorithms.utils import compute_line_image, sgf
from thotus.algorithms.ransac import ransac
from thotus import settings
from thotus.image import tools as imtools

def find_nearest(array,value):
    idx = (np.abs(array-value)).argmin()
    return array[idx]

def find_nearest(a, a0):
    "Element in nd array `a` closest to the scalar value `a0`"
    idx = np.abs(a - a0).argmin()
    return a.flat[idx]

def compute(img, img_g, ref, ref_g, laser_nr=0, mask=None, threshold=None, straight_lines=False):
    x = []
    y = []
    threshold = threshold if threshold is not None else settings.algo_threshold
    denoise = settings.algo_denoise

    bound = 0 if laser_nr == 0 else -1

    blur = (settings.BLUR, settings.BLUR) if settings.BLUR else None
    img = imtools.subtract(img_g, ref_g, mask=mask, blur=blur)
    mask = imtools.compute_noise_mask(img, power=denoise, threshold=threshold)
    img = imtools.mask_contours(img, mask=mask)

    mid = img.shape[1]/2

    for n in range(img.shape[0]):
        max_val = np.max(img[n])
        if max_val > threshold:
            peaks = np.where(img[n] == max_val)[0]
            if peaks.size == 1:
                y.append(n)
                x.append(peaks[0])

    y = np.array(y)
    x = np.array(x)

    if straight_lines:  # line calibration
        s = img.sum(axis=1)
        x = sgf(x, s).astype(np.uint)
        x = ransac( x, y )
    else:
        # TODO: line-denoiser
        pass

    points = (x, y)
    if points:
        return (points, compute_line_image(points, img))
    return None, None

