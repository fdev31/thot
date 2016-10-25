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
from thotus.scanner import Scanner, get_board, get_controllers
from thotus.projection import CalibrationData
from thotus.cloudify import cloudify, meshify
from thotus.ply import save_scene
from thotus import calibration
from thotus import settings

SLOWDOWN = 0

WORKDIR="./capture"

try:
    os.mkdir(WORKDIR)
except:
    pass

COLOR, LASER1, LASER2 = 1, 2, 4 # bit mask
ALL = COLOR | LASER1 | LASER2

calibrate = calibration.calibrate

def toggle_cam_calibration(force_skip=None):
    if force_skip is not None:
        calibration.SKIP_CAM_CALIBRATION = force_skip
    else:
        if calibration.SKIP_CAM_CALIBRATION:
            calibration.SKIP_CAM_CALIBRATION = 0
        else:
            calibration.SKIP_CAM_CALIBRATION = 1
    print("Camera calibration %s"%("disabled" if calibration.SKIP_CAM_CALIBRATION else "enabled"))


def stop():
    global scanner
    if Viewer.instance:
        Viewer.instance.stop()
    if scanner:
        scanner.close()

scanner = None
def get_scanner():
    global scanner
    if not scanner:
        try:
            scanner = Scanner(out=WORKDIR)
        except RuntimeError as e:
            print("Can't init board: %s"%e.args[0])

    scanner.refresh_params()
    return scanner

lasers = False
def switch_lasers():
    global lasers
    lasers = not lasers
    b = get_board()
    if b:
        if lasers:
            b.lasers_on()
        else:
            b.lasers_off()

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
            found, corners = calibration.detectChessBoard(img)
            if found:
                img = calibration.drawChessBoard(img, found, corners)
            gui.display(img, "live", resize=(640,480))

def view():
    if not view_stop():
        Viewer.instance = Viewer()
        Viewer.instance.start()

def view_stop():
    get_scanner() # sync scanner startup
    if Viewer.instance:
        Viewer.instance.stop()
        return True

def capture_color():
    return capture(COLOR)

def capture_lasers():
    return capture(LASER1|LASER2)

def rotate(val):
    s = get_scanner()
    if s:
        s.b.motor_move(int(val))

def _capture_pattern(t):
    s = get_scanner()
    s.motor_move(-50)
    sleep(1)
    if not s:
        return
    try:
        _scan(s, t, angle=100)
        print("")
    except KeyboardInterrupt:
        print("\naborting...")
    s.motor_move(-50)


def capture_pattern():
    _capture_pattern(ALL)

def capture_pattern_lasers():
    _capture_pattern(LASER1|LASER2)

def capture_pattern_colors():
    _capture_pattern(COLOR)

def capture(kind=ALL):

    s = get_scanner()
    if not s:
        return
    try:
        _scan(s, kind)
        print("")
    except KeyboardInterrupt:
        print("\naborting...")

def _scan(b, kind=ALL, definition=1, angle=360):
    view_stop()
    print("scan %d / %d"%(kind, ALL))
    def disp(img, text):
        gui.display(np.rot90(img, 3), text=text, resize=(640,480))

    b.lasers_off()

    for n in range(angle):
        if definition > 1 and n%definition != 0:
            continue
        gui.progress("scan", n, angle)
        b.motor_move(1*definition)
        sleep(0.1) # wait for motor
        b.wait_capture(2+SLOWDOWN, min_val=0.2)
        if kind & COLOR:
            disp( b.save('color_%03d.png'%n) , '')
        if kind & LASER1:
            b.laser_on(0)
            b.wait_capture(2+SLOWDOWN)
            disp( b.save('laser0_%03d.png'%n), 'LEFT')
            b.laser_off(0)
            sleep(0.05)
        if kind & LASER2:
            b.laser_on(1)
            b.wait_capture(2+SLOWDOWN) # sometimes a bit slow to react, so adding one frame
            disp( b.save('laser1_%03d.png'%n) , 'RIGHT')
            b.laser_off(1)
            sleep(0.05)
    gui.clear()

def recognize_pure():
    return recognize(pure_images=True, method='pureimage')


def recognize(pure_images=False, rotated=False, method='pureimage'):
    view_stop()
    calibration_data = settings.load_data(CalibrationData())

    if settings.single_laser is None:
        r = range(2)
    else:
        r = [settings.single_laser]

    obj = cloudify(calibration_data, WORKDIR, r, range(360), pure_images, rotated, method=method)
    save_scene("model.ply", obj)
    gui.clear()

