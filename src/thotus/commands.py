from __future__ import print_function

import os
import json
from time import time, sleep
from threading import Thread
from functools import partial

from thotus.ui import gui
from thotus import settings
from thotus import calibration
from thotus.mesh import meshify
from thotus.boards import Scanner, get_board
from thotus.cloudify import cloudify, iter_cloudify
from thotus.calibration.data import CalibrationData
from thotus.calibration.chessboard import chess_detect, chess_draw

import cv2
import numpy as np
try:
    import pudb
except ImportError:
    pass

COLOR, LASER1, LASER2 = 1, 2, 4 # bit mask
ALL = COLOR | LASER1 | LASER2

scanner = None
lasers = False

EXPOSED_CONTROLS = ["exposure", "brightness"]

def scan(kind=ALL, definition=1, angle=360, calibration=False, on_step=None, display=True):
    """ Low level scan function, main loop, not called directly by shell """
    s = get_scanner()
    if display:
        def disp(img, text):
            gui.display(np.rot90(img, 3), text=text, resize=(640,480))
    else:
        def disp(*a):
            return

    s.lasers_off()
    s.current_rotation = 0

    ftw = 2 # frames to wait
    if calibration:
        ftw += 1


    for n in range(angle):
        if definition > 1 and n%definition != 0:
            continue
        gui.progress("scan", n, angle)
        s.motor_move(1*definition)

        t0 = time()
        if on_step:
            on_step()

        s.wait_capture(ftw,
                minus=time()-t0,
                min_val=0.1
                )
        if kind & COLOR:
            disp( s.save('color_%03d.%s'%(n, settings.FILEFORMAT)) , '')
        if kind & LASER1:
            s.laser_on(0)
            s.wait_capture(ftw)
            disp( s.save('laser0_%03d.%s'%(n, settings.FILEFORMAT)), 'laser 1')
            s.laser_off(0)
        if kind & LASER2:
            s.laser_on(1)
            s.wait_capture(ftw)
            disp( s.save('laser1_%03d.%s'%(n, settings.FILEFORMAT)) , 'laser 2')
            s.laser_off(1)
    gui.clear()

def get_camera_controllers():
    s = get_scanner()
    o = {}
    if not s:
        return o
    def _shellwrapper(control, prop):
        def getsetter(p=None):
            if p is None:
                print(getattr(control, prop))
            else:
                setattr(control, prop, int(p))
        return getsetter
    for n in EXPOSED_CONTROLS:
        o["cam_"+n] = _shellwrapper(s.cap_ctl, n)
    return o

def get_scanner():
    global scanner
    if not scanner:
        try:
            scanner = Scanner(out=settings.WORKDIR)
        except RuntimeError as e:
            print("Can't init board: %s"%e.args[0])
    return scanner

def toggle_interactive_calibration():
    settings.interactive_calibration = not settings.interactive_calibration
    print("Camera calibration set to %s"%("interactive" if settings.interactive_calibration else "automatic"))
    return 3

def switch_lasers():
    """ Toggle lasers """
    global lasers
    lasers = not lasers
    b = get_board()
    if b:
        if lasers:
            b.lasers_on()
        else:
            b.lasers_off()
    return 3


def rotate(val):
    """ Rotates the platform by X degrees """
    s = get_scanner()
    if s:
        s.motor_move(int(val))

class Viewer(Thread):
    instance = None
    running = True

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
            self.running = False

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
    view_stop()
    if scanner:
        scanner.close()

def capture_pattern():
    " Capture chessboard pattern "
    t = ALL
    s = get_scanner()
    old_out = s.out
    s.out = settings.CALIBDIR
    s.current_rotation = 0
    s.motor_move(-50)
    sleep(2)
    view_stop()
    if not s:
        return
    try:
        scan(t, angle=100, definition=3, calibration=True)
        print("")
    except KeyboardInterrupt:
        s.reset_motor_rotation()
        print("\naborting...")
    except Exception:
        s.out = old_out
        s.reset_motor_rotation()
        raise
    else:
        s.out = old_out
        s.reset_motor_rotation()

def capture_color():
    " Capture images (color only)"
    return capture(COLOR)

def capture_lasers():
    " Capture images (lasers only) [puremode friendly]"
    return capture(LASER1|LASER2)

def capture(kind=ALL, on_step=None, display=True):
    " Capture images "
    view_stop()
    s = get_scanner()
    if not s:
        return
    try:
        scan(kind, on_step=on_step, display=display)
        print("")
    except KeyboardInterrupt:
        print("\naborting...")

    s.reset_motor_rotation()

def recognize(rotated=False):
    " Compute mesh from images (pure mode aware)"
    view_stop()
    calibration_data = settings.load_data(CalibrationData())

    r = settings.get_laser_range()

    slices, colors = cloudify(calibration_data, settings.WORKDIR, r, range(360), rotated, method=settings.SEGMENTATION_METHOD)
    meshify(calibration_data, slices, colors=colors, cylinder=settings.ROI).save("model.ply")
    gui.clear()

def shot():
    """ Save pattern image for later camera calibration """
    name = os.path.abspath( os.path.join(settings.SHOTSDIR, "%s.%s"%(int(time()), settings.FILEFORMAT)) )
    get_scanner().save(name)

def shots_clear():
    """ Remove all shots """
    for fn in os.listdir(settings.SHOTSDIR):
        if fn.endswith(settings.FILEFORMAT):
            os.unlink(os.path.join(settings.SHOTSDIR, fn))

def toggle_pure_mode():
    settings.pure_mode = not settings.pure_mode
    print("Pure mode on, you must capture lasers in obscurity now"
            if settings.pure_mode else "Pure mode off")

def set_roi(val1=None, val2=None):
    """ Set with and height of the scanning cylinder, in mm (only one value = height) """
    if val1 is None:
        print("Diameter: %dmm Height: %dmm"%settings.ROI)
    else:
        if not val2:
            val2 = val1
            val1 = settings.ROI[0]
        settings.ROI = (int(val1), int(val2))
        set_roi()

def set_horus_cfg():
    " Load horus calibration configuration "
    settings.configuration = 'horus'

def set_thot_cfg():
    " Load thot calibration configuration "
    settings.configuration = 'thot'

def set_algo_value(param=None, value=None):
    """ List, get or set algorithm parameters """
    if param is None:
        for n in dir(settings):
            if n.startswith('algo_'):
                set_algo_value(n[5:])
        return
    if value is None:
        print("%s = %s"%(param, getattr(settings, 'algo_' + param)))
        return
    try:
        if '.' in value:
            value = float(value)
        else:
            value = int(value)
    except TypeError:
        pass
    setattr(settings, 'algo_' + param, value)

def set_single_laser(laser_number=None):
    """ Set dual scanning (no param) or a single laser (1 or 2)  """
    if laser_number is None:
        settings.single_laser = None
    else:
        i = int(laser_number)
        if i not in (1, 2):
            print("Laser number must be 1 or 2")
        settings.single_laser = i-1

def set_algorithm(name=None):
    """ Change the algorithm for laser detection one of: uncanny, pureimages """
    if name is None:
        print(settings.SEGMENTATION_METHOD)
    else:
        settings.SEGMENTATION_METHOD = name.strip().lower()

def scan_object():
    """ Scan object """
    calibration_data = settings.load_data(CalibrationData())

    r = settings.get_laser_range()

    cloudifier = iter_cloudify(calibration_data, settings.WORKDIR, r, range(360), False, method=settings.SEGMENTATION_METHOD)
    iterator = partial(next, cloudifier)

    capture(on_step=iterator, display=False)

    slices, colors = iterator()
    r = meshify(calibration_data, slices, colors=colors).save("model.ply")
    gui.clear()
    return r

def calibrate():
    view_stop()
    return calibration.calibrate()

def calibrate_cam_from_shots():
    view_stop()
    calibration.calibrate_cam_from_shots()
    try:
        return calibrate()
    except Exception:
        print("Don't forget to make the calibration again !")

def stdcalibrate():
    """ start platform & laser calibration """
    capture_pattern()
    return calibrate()

