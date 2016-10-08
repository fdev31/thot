from __future__ import print_function

import sys
import cv2
from scipy.misc import imresize

class GUI:
    def progress(self, text, val, total=100):
        print("\r%s %d/%d # %3d%%"%(text, val, total, int(100.0*val/total)), end='')
        sys.stdout.flush()

    def display(self, image, text, resize=None):
        if resize:
            image = image.copy()
        if text:
            cv2.putText(image, text, (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (255, 255, 255))

        if resize:
            image = imresize(image, resize)
        cv2.imshow('frame', image)
        while cv2.waitKey(100) > 0:
            pass

gui = GUI()
