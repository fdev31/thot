from thotus.algorithms.ransac import ransac, sgf

import numpy as np
import cv2

def find_nearest(array,value):
    return (np.abs(array-value)).argmin()

def find_subsequence(seq, subseq):
    target = np.dot(subseq, subseq)
    candidates = np.where(np.correlate(seq,
                                       subseq, mode='valid') == target)[0]
    # some of the candidates entries may be false positives, double check
    check = candidates[:, np.newaxis] + np.arange(len(subseq))
    mask = np.all((np.take(seq, check) == subseq), axis=-1)
    return candidates[mask]

def compute_line_image(points, image):
    if points is not None:
        u, v = points
        image = np.zeros_like(image)
        try:
            image[v.astype(int), np.around(u).astype(int) - 1] = 255
            image[v.astype(int), np.around(u).astype(int)] = 255
            image[v.astype(int), np.around(u).astype(int) + 1] = 255
        except IndexError:
            pass
        return image


