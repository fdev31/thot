from __future__ import print_function

import os
import json
import pickle
from time import sleep
from threading import Thread

from thotus.ui import gui
from thotus import calibration
from thotus import settings
from thotus import control
from thotus.ply import save_scene
from thotus.cloudify import cloudify
from thotus.projection import CalibrationData
from thotus.chessboard import chess_detect, chess_draw

import cv2
import numpy as np
try:
    import pudb
except ImportError:
    pass

# aliases
get_scanner = control.get_scanner
calibrate = calibration.calibrate

def calibrate_pure():
    " start platform & laser calibration (assume laser images are pure) "
    return calibration.calibrate(pure_laser=True)

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

def capture(kind=control.ALL):
    " Capture images "
    view_stop()
    if not s:
        return
    try:
        control.scan(kind)
        print("")
    except KeyboardInterrupt:
        print("\naborting...")

    s.reset_motor_rotation()

def recognize_pure():
    " Compute mesh from images (assume laser images are pure) "
    return recognize(pure_images=True, method='pureimage')

def recognize(pure_images=False, rotated=False, method='pureimage'):
    " Compute mesh from images "
    view_stop()
    calibration_data = settings.load_data(CalibrationData())

    if settings.single_laser is None:
        r = range(2)
    else:
        r = [settings.single_laser]

    obj = cloudify(calibration_data, settings.WORKDIR, r, range(360), pure_images, rotated, method=method)
    save_scene("model.ply", obj)
    gui.clear()

