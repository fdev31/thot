from thotus.algorithms.utils import compute_line_image
from thotus.algorithms.ransac import ransac
import numpy as np
import cv2

def compute(img, laser_nr, threshold=10, use_ransac=False):
    x = []
    y = []
    img = cv2.blur(img, (5, 5))

    bound = 0 if laser_nr == 0 else -1

    for n in range(img.shape[0]):
        max_val = np.max(img[n])
        if max_val < threshold:
            continue
        peaks = np.where(img[n] == max_val)[0]
        y.append(n)
        x.append(peaks[bound])

    y = np.array(y)
    x = np.array(x)

    if use_ransac:  # line calibration
        x = ransac( x, y )

    points = (x, y)
    if points:
        return (points, compute_line_image(points, img))
    return None, None

