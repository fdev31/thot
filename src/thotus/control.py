from time import sleep, time

from thotus.boards import Scanner, get_board
from thotus import settings
from thotus.ui import gui

import numpy as np

COLOR, LASER1, LASER2 = 1, 2, 4 # bit mask
ALL = COLOR | LASER1 | LASER2

scanner = None
lasers = False

EXPOSED_CONTROLS = ["exposure", "brightness"]

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

def scan(kind=ALL, definition=1, angle=360, calibration=False, on_step=None, display=True):
    s = get_scanner()
    if display:
        def disp(img, text):
            gui.display(np.rot90(img, 3), text=text, resize=(640,480))
    else:
        def disp(*a):
            return

    s.lasers_off()
    D = 0.03

    ftw = 1 # frames to wait
    if calibration: # Be 100% sure :P
        ftw += 1

    for n in range(angle):
        if definition > 1 and n%definition != 0:
            continue
        gui.progress("scan", n, angle)
        s.motor_move(1*definition)
        if definition <= 2:
            sleep(0.02)
        else:
            sleep(0.06* definition)

        t0 = time()
        if on_step:
            on_step()

        s.wait_capture(ftw)
        if kind & COLOR:
            disp( s.save('color_%03d.%s'%(n, settings.FILEFORMAT)) , '')
        if kind & LASER1:
            s.laser_on(0)
            sleep(D)
            s.wait_capture(ftw)
            disp( s.save('laser0_%03d.%s'%(n, settings.FILEFORMAT)), 'laser 1')
            s.laser_off(0)
        if kind & LASER2:
            s.laser_on(1)
            sleep(D)
            s.wait_capture(ftw)
            disp( s.save('laser1_%03d.%s'%(n, settings.FILEFORMAT)) , 'laser 2')
            s.laser_off(1)
    gui.clear()

def rotate(val):
    """ Rotates the platform by X degrees """
    s = get_scanner()
    if s:
        s.motor_move(int(val))
