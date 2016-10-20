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
from thotus.calibration import calibrate
from thotus.cloudify import cloudify, meshify
from thotus.ply import save_scene
from thotus.settings import load_data

SLOWDOWN = 0

WORKDIR="./capture"

try:
    os.mkdir(WORKDIR)
except:
    pass

COLOR, LASER1, LASER2 = 1, 2, 4 # bit mask
ALL = COLOR | LASER1 | LASER2

def stop():
    global scanner
    if scanner:
        scanner.close()
    if Viewer.instance:
        Viewer.instance.stop()

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
            gui.display(np.rot90(s.cap.buff, 3), "live", resize=(640,480))

def remesh():
    cd = _load_calibration_data()
#    cd.laser_planes[0].distance += 0.5
    obj = meshify(cd)
    save_scene("model.ply", obj)

def view():
    get_scanner() # sync scanner startup
    if Viewer.instance:
        Viewer.instance.stop()
    else:
        Viewer.instance = Viewer()
        Viewer.instance.start()

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

def capture_pattern_lasers():
    _capture_pattern(LASER1|LASER2)

def capture_pattern_colors():
    _capture_pattern(COLOR)

def capture(kind=ALL):
    print("Capture %d"%kind)
    s = get_scanner()
    if not s:
        return
    try:
        _scan(s, kind)
        print("")
    except KeyboardInterrupt:
        print("\naborting...")

def _scan(b, kind=ALL, definition=1, angle=360):
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
        if kind & LASER2:
            b.laser_on(1)
            b.wait_capture(2+SLOWDOWN) # sometimes a bit slow to react, so adding one frame
            disp( b.save('laser1_%03d.png'%n) , 'RIGHT')
            b.laser_off(1)
    gui.clear()

def recognize_pure():
    return recognize(pure_images=True, method='simpleline')

def _load_calibration_data():
    path = os.path.expanduser('~/.horus/calibration.json')
    settings = json.load(open(path))['calibration_settings']
    calibration_data = CalibrationData()

    calibration_data.distortion_vector = np.array(settings['distortion_vector']['value'])
    calibration_data.camera_matrix = np.array( settings['camera_matrix']['value'] )

    calibration_data.laser_planes[0].distance = settings['distance_left']['value']
    calibration_data.laser_planes[0].normal = settings['normal_left']['value']
    calibration_data.laser_planes[1].distance = settings['distance_right']['value']
    calibration_data.laser_planes[1].normal = settings['normal_right']['value']

    calibration_data.platform_rotation = settings['rotation_matrix']['value']
    calibration_data.platform_translation = settings['translation_vector']['value']
    return calibration_data

def recognize(pure_images=False, rotated=False, method='simpleline'):
    calibration_data = _load_calibration_data()

#    calibration_data._roi = (9, 8, 1262, 942) # hardcoded ROI
#    load_data(calibration_data) # overwrite with custom settings

    obj = cloudify(calibration_data, WORKDIR, range(2), range(360), pure_images, rotated, method=method)
    save_scene("model.ply", obj)
    gui.clear()

