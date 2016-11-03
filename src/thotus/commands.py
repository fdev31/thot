from __future__ import print_function

import os
from time import time, sleep
from threading import Thread
from functools import partial

from thotus.ui import gui
from thotus import settings
from thotus import calibration
from thotus.mesh import meshify
from thotus.boards import Scanner, get_board
from thotus.cloudify import cloudify, iter_cloudify, LineMaker
from thotus.calibration.data import CalibrationData
from thotus.calibration.chessboard import chess_detect, chess_draw

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

def scan(kind=ALL, definition=1, angle=360, calibration=False, on_step=None, display=True, ftw=None):
    """ Low level scan function, main loop, not called directly by shell """
    s = get_scanner()
    if display:
        def disp(img, text):
            if settings.ROTATE:
                img = np.rot90(img, settings.ROTATE)
            gui.display(img, text=text, resize=True)
    else:
        def disp(*a):
            return

    s.lasers_off()
    s.current_rotation = 0

    if ftw is None:
        ftw = settings.SYNC_FRAME_STD

    if calibration:
        ftw += 1

    sleep(0.2)

    for n in range(angle):
        if definition > 1 and n%definition != 0:
            continue
        gui.progress("scan", n, angle)
        s.motor_move(1*definition)
        slowdown = 1 if n == 0 else 0 # XXX: first frame needs more time (!)

        if on_step:
            on_step()
        else:
            sleep(0.13) # wait motor

        if calibration:
            sleep(0.05*definition)

        if kind & COLOR:
            s.wait_capture(ftw+slowdown)
            disp( s.save('color_%03d.%s'%(n, settings.FILEFORMAT)) , '')
        if kind & LASER1:
            s.laser_on(0)
            s.wait_capture(ftw+slowdown)
            disp( s.save('laser0_%03d.%s'%(n, settings.FILEFORMAT)), 'laser 1')
            s.laser_off(0)
        if kind & LASER2:
            s.laser_on(1)
            s.wait_capture(ftw+slowdown)
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

    line_mode = False

    def stop(self):
        self.running = False
        self.join()
        self.__class__.instance = None
        gui.clear()

    def run(self):
        lm = LineMaker()
        try:
            s = get_scanner()
            if s is None:
                raise ValueError()
        except Exception as e:
            print("Unable to init scanner, not starting viewer.")
            self.running = False

        while self.running:
            img = s.cap.get(1)
            if settings.ROTATE:
                img = np.rot90(img, settings.ROTATE)
            if self.line_mode:
                lineprocessor = getattr(lm, 'from_'+settings.SEGMENTATION_METHOD)
                s.laser_on(0)
                laser_image = s.cap.get(1)
                if settings.ROTATE:
                    laser_image = np.rot90(laser_image, settings.ROTATE)
                s.laser_off(0)
                points, processed = lineprocessor(laser_image, laser_image[:,:,0], img, img[:,:,0])
                img = processed
            else:
                grey = img[:,:,1]
                found, corners = chess_detect(grey)
                if found:
                    img = chess_draw(grey, found, corners)
            gui.display(img, "live", resize=True)

def view_mode():
    Viewer.instance.line_mode = not Viewer.instance.line_mode
    return 3

def view():
    " toggle webcam output (show chessboard if detected)"
    if not view_stop():
        Viewer.instance = Viewer()
        Viewer.instance.start()
    return 3

def view_stop():
    if Viewer.instance and Viewer.instance.running:
        get_scanner() # sync scanner startup
        Viewer.instance.stop()
        return True

def stop():
    settings.save_profile()
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
    return 3

def capture_color():
    " Capture images (color only)"
    return capture(COLOR)

def capture_lasers():
    " Capture images (lasers only) [puremode friendly]"
    return capture(LASER1|LASER2)

def capture(kind=ALL, on_step=None, display=True, ftw=None):
    " Capture images "
    if ftw is None:
        ftw = settings.SYNC_FRAME_STD
    view_stop()
    s = get_scanner()
    if not s:
        return
    try:
        scan(kind, on_step=on_step, display=display, ftw=ftw)
        print("")
    except KeyboardInterrupt:
        print("\naborting...")

    s.reset_motor_rotation()
    return 3

def recognize():
    " Compute mesh from images (pure mode aware)"
    view_stop()
    calibration_data = settings.load_data(CalibrationData())

    r = settings.get_laser_range()

    slices, colors = cloudify(calibration_data, settings.WORKDIR, r, range(360), method=settings.SEGMENTATION_METHOD)
    meshify(calibration_data, slices, colors=colors, cylinder=settings.ROI).save("model.ply")
    gui.clear()

def shot():
    """ Save pattern image for later camera calibration """
    name = os.path.abspath( os.path.join(settings.SHOTSDIR, "%s.%s"%(int(time()), settings.FILEFORMAT)) )
    get_scanner().save(name)
    print("ok")
    return 3

def shots_clear():
    """ Remove all shots """
    for fn in os.listdir(settings.SHOTSDIR):
        if fn.endswith(settings.FILEFORMAT):
            os.unlink(os.path.join(settings.SHOTSDIR, fn))
    print("ok")
    return 3

def toggle_pure_mode():
    settings.pure_mode = not settings.pure_mode
    print("Pure mode on, you must capture lasers in obscurity now"
            if settings.pure_mode else "Pure mode off")
    return 3

def set_roi(val1=None, val2=None):
    """ Set with and height of the scanning cylinder, in mm (only one value = height) """
    if val1 is None:
        h = settings.ROI[0]/10.0
        d = settings.ROI[1]/10.0

        print("Height: %.1fcm Diameter: %.1fcm"%(h, d))
    else:
        if not val2:
            val2 = settings.ROI[1]/5
        settings.ROI = (int(float(val1)*10), int(float(val2)*10))
        set_roi() # print
    return 3

def set_cfg(what=None, val=None, val2=None):
    " Set, get or list configuration settings "
    if what is None:
        for n in settings._persist:
            print("%s = %s"%(n, getattr(settings, n)))
    elif val is None:
        print("%s = %s"%(what, getattr(settings, what)))
    else: # set
        o = getattr(settings, what)
        if isinstance(o, int):
            val = int(val)
        elif isinstance(o, float):
            val = float(val)
        elif isinstance(o, str):
            pass
        else: # array of int
            if val2 is None:
                val2 = o[1]
            else:
                val2 = int(val2)
            val = int(val)
        if val2:
            setattr(settings, what, (val, val2))
        else:
            setattr(settings, what, val)
    return 3


def set_horus_cfg():
    " Load horus calibration configuration "
    settings.configuration = 'horus'
    return 3

def set_thot_cfg():
    " Load thot calibration configuration "
    settings.configuration = 'thot'
    return 3

def set_algo_value(param=None, value=None):
    """ List, get or set algorithm parameters """
    if param is None:
        for n in dir(settings):
            if n.startswith('algo_'):
                set_algo_value(n[5:])
        return 3
    if value is None:
        print("%s = %s"%(param, getattr(settings, 'algo_' + param)))
        return 3
    try:
        if '.' in value:
            value = float(value)
        else:
            value = int(value)
    except TypeError:
        pass
    setattr(settings, 'algo_' + param, value)
    return 3

def set_single_laser(laser_number=None):
    """ Set dual scanning (no param) or a single laser (1 or 2)  """
    if laser_number is None:
        settings.single_laser = None
    else:
        i = int(laser_number)
        if i not in (1, 2):
            print("Laser number must be 1 or 2")
        settings.single_laser = i-1
    return 3

def set_algorithm(name=None):
    """ Change the algorithm for laser detection one of: uncanny, pureimages """
    if name is None:
        print(settings.SEGMENTATION_METHOD)
    else:
        settings.SEGMENTATION_METHOD = name.strip().lower()
    return 3

def scan_object():
    """ Scan object """
    calibration_data = settings.load_data(CalibrationData())

    r = settings.get_laser_range()

    cloudifier = iter_cloudify(calibration_data, settings.WORKDIR, r, range(360), method=settings.SEGMENTATION_METHOD)
    iterator = partial(next, cloudifier)

    capture(on_step=iterator, display=False, ftw=settings.SYNC_FRAME_FAST)

    slices, colors = iterator()
    meshify(calibration_data, slices, colors=colors).save("model.ply")
    gui.clear()

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

