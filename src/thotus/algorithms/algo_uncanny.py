from thotus.algorithms.utils import compute_line_image
from thotus.algorithms.ransac import ransac
import numpy as np
import cv2

def compute(img, laser_nr, use_ransac=False):
    u = []
    v = []
    line_map = cv2.Canny(img,50,200)
    for n in range(line_map.shape[0]):
        r = np.where(line_map[n] == 255)[0]
        if r.size > 0:
            if r.size == 2:
                v.append(n)
                u.append( int(np.average(r)+0.5))
    if u:
        points = [np.array(u),np.array(v)]

        if use_ransac:
            points[0] = ransac( points[0], points[1])
        return points, compute_line_image(points, img)
    return None, None

