import os
import sys
import json
import math
import pickle
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
    METADATA = defaultdict(lambda: {})
    camera.METADATA = platform.METADATA = lasers.METADATA = METADATA

    calibration_data = data.CalibrationData()

    img_mask = settings.CALIBDIR + '/color_*.' + settings.FILEFORMAT
    img_names = sorted(glob(img_mask))[::FAST_CALIBRATE]

    camera.calibration(calibration_data, img_names)
    buggy_captures = platform.calibration(calibration_data)

    good_images = set(METADATA)
    good_images.difference_update(buggy_captures)
    good_images = list(good_images)
    good_images.sort()
    pickle.dump(dict(
            images = good_images,
            metadata = dict(METADATA),
            )
            , open('images.js', 'wb'))

    lasers.calibration(calibration_data, good_images, pure_laser)
    settings.save_data(calibration_data)
    METADATA.clear()
    gui.clear()
