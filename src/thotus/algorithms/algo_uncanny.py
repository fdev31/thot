from thotus.image import tools as imtools
from thotus.algorithms.utils import compute_line_image
from thotus.algorithms.ransac import ransac
from thotus import settings
import numpy as np
import cv2

def compute(img, img_g, ref, ref_g, laser_nr=0, mask=None, straight_lines=False):
    u = []
    v = []

    threshold = threshold if threshold is not None else settings.algo_threshold
    denoise = settings.algo_denoise

    img = imtools.subtract(img_g, ref_g, blur=(5, 10), mask=mask)
    mask = imtools.compute_noise_mask(img, power=denoise, threshold=threshold)
    img = imtools.mask_contours(img, mask=mask)

    line_map = cv2.Canny(img,50,200)

    for n in range(line_map.shape[0]):
        r = np.where(line_map[n] == 255)[0]
        if r.size > 0:
            if r.size == 2:
                v.append(n)
                u.append( int(np.average(r)+0.5))
    if u:
        points = [np.array(u),np.array(v)]

        if straight_lines:
            points[0] = ransac( points[0], points[1])
        return points, compute_line_image(points, img)
    return None, None

