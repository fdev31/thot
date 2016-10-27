import os
import sys
import math
from glob import glob
from collections import defaultdict


from thotus import settings
from thotus.ui import gui

import cv2
import numpy as np

FAST_CALIBRATE = 1 # 1 for full calibration, > 1 for grosser calibration

def calibrate(pure_laser=False):
    " Compute calibration data from images "
    from . import camera, platform, lasers, data

    calibration_data = data.CalibrationData()

    img_mask = settings.CALIBDIR + '/color_*.' + settings.FILEFORMAT
    img_names = sorted(glob(img_mask))[::FAST_CALIBRATE]

    calib_settings = camera.calibration(calibration_data, img_names)
    buggy_captures = platform.calibration(calibration_data, calib_settings)

    good_images = set(calib_settings)
    good_images.difference_update(buggy_captures)
    good_images = list(good_images)
    good_images.sort()

    lasers.calibration(calibration_data, calib_settings, good_images, pure_laser)
    settings.save_data(calibration_data)
    gui.clear()
