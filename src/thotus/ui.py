from __future__ import print_function

import sys
import cv2
from scipy.misc import imresize

class GUI:
    def __init__(self):
        cv2.namedWindow('output')

    def progress(self, text, val, total=100):
        print("\r%s [%d] @ %3d%%"%(text, val, int(100.0*val/total)), end='')
        sys.stdout.flush()

    def clear(self):
        cv2.destroyWindow('output')
        cv2.imshow('output', 0)
        self._wk()

    def _wk(self):
        while cv2.waitKey(10) > 0:
            pass

    def display(self, image, text, resize=None):
        if resize:
            image = image.copy()
        if text:
            black = (0, 0, 0)
            white = (255, 255, 255)
            cv2.putText(image, text, (9, 99), cv2.FONT_HERSHEY_SIMPLEX, 2.0, black)
            cv2.putText(image, text, (12, 102), cv2.FONT_HERSHEY_SIMPLEX, 2.0, black)
            cv2.putText(image, text, (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 2.0, white)
            cv2.putText(image, text, (11, 101), cv2.FONT_HERSHEY_SIMPLEX, 2.0, white)

        if resize:
            image = imresize(image, resize)
        cv2.imshow('output', image)
        self._wk()

gui = GUI()
