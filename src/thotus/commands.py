from __future__ import print_function

import os
import json
import pickle
from time import sleep
from threading import Thread

from thotus.ui import gui
from thotus import settings
from thotus import control
from thotus import calibration
from thotus.cloudify import meshify, cloudify, iter_cloudify
from thotus.calibration.data import CalibrationData
from thotus.calibration.chessboard import chess_detect, chess_draw

import cv2
import numpy as np
try:
    import pudb
except ImportError:
    pass

# aliases
get_scanner = control.get_scanner

class Viewer(Thread):
    instance = None
    running = None

    def stop(self):
        self.running = False
        self.join()
        self.__class__.instance = None
        gui.clear()

    def run(self):
        try:
            s = get_scanner()
        except Exception as e:
            print("Unable to init scanner, not starting viewer.")
            return

        self.running = True
        while self.running:
            s.wait_capture(1)
            img = np.rot90(s.cap.buff, 3)
            grey = img[:,:,1]
            found, corners = chess_detect(grey)
            if found:
                img = chess_draw(grey, found, corners)
            gui.display(img, "live", resize=(640,480))

def view():
    " toggle webcam output (show chessboard if detected)"
    if not view_stop():
        Viewer.instance = Viewer()
        Viewer.instance.start()

def view_stop():
    if Viewer.instance and Viewer.instance.running:
        get_scanner() # sync scanner startup
        Viewer.instance.stop()
        return True

def stop():
    if view_stop():
        get_scanner().close()

def capture_pattern():
    " Capture chessboard pattern "
    control.capture_pattern(control.ALL)

def capture_pattern_lasers():
    " Capture chessboard pattern (lasers only) "
    control.capture_pattern(control.LASER1|control.LASER2)

def capture_pattern_colors():
    " Capture chessboard pattern (color only) "
    control.capture_pattern(control.COLOR)

def capture_color():
    " Capture images (color only) "
    return capture(control.COLOR)

def capture_lasers():
    " Capture images (lasers only) "
    return capture(control.LASER1|control.LASER2)

def capture(kind=control.ALL, step=None):
    " Capture images "
    view_stop()
    if not s:
        return
    try:
        control.scan(kind, step=step)
        print("")
    except KeyboardInterrupt:
        print("\naborting...")

    s.reset_motor_rotation()

def recognize_pure():
    " Compute mesh from images (assume laser images are pure) "
    return recognize(pure_images=True, method='pureimage')

def recognize(pure_images=False, rotated=False, method='uncanny'):
    " Compute mesh from images "
    view_stop()
    calibration_data = settings.load_data(CalibrationData())

    r = settings.get_laser_range()

    slices, colors = cloudify(calibration_data, settings.WORKDIR, r, range(360), pure_images, rotated, method=method)
    meshify(calibration_data, slices).save("model.ply")
    gui.clear()

def set_horus_cfg():
    " Load horus calibration configuration "
    settings.configuration = 'horus'

def set_thot_cfg():
    " Load thot calibration configuration "
    settings.configuration = 'thot'

def set_single_laser(laser_number):
    i = int(laser_number)
    if i not in (1, 2):
        print("Laser number must be 1 or 2")
    settings.single_laser = i-1

def set_dual_laser():
    settings.single_laser = None

def scan():
    """ Scan object """
    calibration_data = settings.load_data(CalibrationData())

    r = settings.get_laser_range()

    cloudifier = iter_cloudify(calibration_data, settings.WORKDIR, r, range(360), False, False, method='pureimage')

    capture(step=cloudifier.next)
    slices, colors = next(cloudifier)
    meshify(calibration_data, slices).save("model.ply")
    gui.clear()

    return recognize()

calibrate = calibration.calibrate

def calibrate_pure():
    " start platform & laser calibration (assume laser images are pure) "
    return calibrate(pure_laser=True)

def fullcalibrate():
    """ start a full calibration, including camera intrinsics """
    capture_pattern()
    toggle_cam_calibration(False)
    return calibrate()

def stdcalibrate():
    """ start platform & laser calibration """
    capture_pattern()
    toggle_cam_calibration(True)
    return calibrate()
