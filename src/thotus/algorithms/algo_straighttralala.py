import numpy as np
import cv2

from thotus.algorithms.utils import compute_line_image
from thotus.algorithms.ransac import ransac
from thotus import settings
from thotus.image import tools as imtools

def compute(img, img_g, ref, ref_g, laser_nr=0, mask=None, threshold=None):
    x = []
    y = []
    threshold = threshold if threshold is not None else settings.algo_threshold
    denoise = settings.algo_denoise

    bound = 0 if laser_nr == 0 else -1

    blur = (settings.BLUR, settings.BLUR) if settings.BLUR else None
    img = imtools.subtract(img_g, ref_g, mask=mask, blur=blur)

    prev = img.shape[1]/2

    def append_point(nr, val):
        Y = 10
        if val > Y and val < img.shape[1] - Y:
            y.append(nr)
            x.append(val)

    for n in range(img.shape[0]):
        line = np.convolve(img[n], [1, 2, 1])
        max_val = np.max(line)
        if max_val > threshold:
            peaks = np.where(line == max_val)[0]
            if peaks.size == 1:
                # try to fix first
                cur = peaks[0]
                D = 10
                if abs(cur-prev) > D:
                    off = max(0, prev-D)
                    new_peak = np.max(line[int(off):int(min(line.size, prev+D))])
                    if line[new_peak] >= line[cur]/3:
                        cur = new_peak
                append_point(n, cur)
            if x:
                prev = x[-1]

    y = np.array(y)
    x = np.array(x)

    max_entro = img.shape[1]/4
    if np.std(x) < max_entro and x.size > 10:
        x = ransac( x, y )

        points = (x, y)
        if points:
            return (points, compute_line_image(points, img))
    return None, None

