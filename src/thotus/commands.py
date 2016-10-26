from __future__ import print_function

import os
import json
import pickle
from threading import Thread

try:
    import pudb
except ImportError:
    pass
import cv2
import numpy as np
from time import sleep

from thotus.ui import gui
from thotus.projection import CalibrationData
from thotus.cloudify import cloudify
from thotus.ply import save_scene
from thotus import calibration
from thotus import settings
from thotus import control

# aliases
calibrate = calibration.calibrate
get_scanner = control.get_scanner

def calibrate_pure():
    return calibrate(pure_laser=True)

class Viewer(Thread):
    instance = None

    def stop(self):
        self.running = False
        self.join()
        self.__class__.instance = None
        gui.clear()

    def run(self):
        s = get_scanner()
        self.running = True
        while self.running:
            s.wait_capture(1)
            img = np.rot90(s.cap.buff, 3)
            grey = img[:,:,1]
            found, corners = calibration.detectChessBoard(grey)
            if found:
                img = calibration.drawChessBoard(grey, found, corners)
            gui.display(img, "live", resize=(640,480))

def view():
    if not view_stop():
        Viewer.instance = Viewer()
        Viewer.instance.start()

def view_stop():
    if Viewer.instance:
        get_scanner() # sync scanner startup
        Viewer.instance.stop()
        return True

def stop():
    if view_stop():
        get_scanner().close()

def capture_color():
    return capture(control.COLOR)

def capture_lasers():
    return capture(control.LASER1|control.LASER2)

def capture_pattern():
    control.capture_pattern(control.ALL)

def capture_pattern_lasers():
    control.capture_pattern(control.LASER1|control.LASER2)

def capture_pattern_colors():
    control.capture_pattern(control.COLOR)

def capture(kind=control.ALL):
    view_stop()
    s = get_scanner()
    if not s:
        return
    try:
        control.scan(s, kind)
        print("")
    except KeyboardInterrupt:
        print("\naborting...")


def recognize_pure():
    return recognize(pure_images=True, method='pureimage')

def recognize(pure_images=False, rotated=False, method='pureimage'):
    view_stop()
    calibration_data = settings.load_data(CalibrationData())

    if settings.single_laser is None:
        r = range(2)
    else:
        r = [settings.single_laser]

    obj = cloudify(calibration_data, settings.WORKDIR, r, range(360), pure_images, rotated, method=method)
    save_scene("model.ply", obj)
    gui.clear()

