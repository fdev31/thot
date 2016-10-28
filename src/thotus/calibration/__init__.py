import os
import sys
import math
from glob import glob
from collections import defaultdict


from thotus import settings
from thotus.ui import gui

import cv2
import numpy as np

def calibrate_cam_from_shots():
    " Compute camera calibration data from shots "
    from . import camera, data
    sk = settings.skip_calibration
    settings.skip_calibration = False

    calibration_data = data.CalibrationData()

    img_mask = settings.SHOTSDIR + '/*.' + settings.FILEFORMAT
    img_names = sorted(glob(img_mask))
    camera.calibration(calibration_data, img_names)
    settings.skip_calibration = sk
    gui.clear()

def calibrate():
    " Compute calibration data from images "
    from . import camera, platform, lasers, data

    calibration_data = data.CalibrationData()

    img_mask = settings.CALIBDIR + '/color_*.' + settings.FILEFORMAT
    img_names = sorted(glob(img_mask))

    calib_settings = camera.calibration(calibration_data, img_names)
    buggy_captures = platform.calibration(calibration_data, calib_settings)

    good_images = set(calib_settings)
    good_images.difference_update(buggy_captures)
    good_images = list(good_images)
    good_images.sort()

    lasers.calibration(calibration_data, calib_settings, good_images)
    settings.save_data(calibration_data)
    gui.clear()
