from time import sleep

from thotus.scanner import Scanner, get_board
from thotus import calibration
from thotus import settings
from thotus.ui import gui

import numpy as np

COLOR, LASER1, LASER2 = 1, 2, 4 # bit mask
ALL = COLOR | LASER1 | LASER2
SLOWDOWN = 0

scanner = None
lasers = False

def get_scanner():
    global scanner
    if not scanner:
        try:
            scanner = Scanner(out=settings.WORKDIR)
        except RuntimeError as e:
            print("Can't init board: %s"%e.args[0])

    scanner.refresh_params()
    return scanner

def toggle_cam_calibration(force_skip=None):
    if force_skip is not None:
        settings.skip_calibration = force_skip
    else:
        if settings.skip_calibration:
            settings.skip_calibration = False
        else:
            settings.skip_calibration = True

    print("Camera calibration %s"%("disabled" if calibration.SKIP_CAM_CALIBRATION else "enabled"))

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

def scan(b, kind=ALL, definition=1, angle=360, calibration=False):
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
            disp( b.save('color_%03d.%s'%(n, settings.FILEFORMAT)) , '')
        if kind & LASER1:
            b.laser_on(0)
            b.wait_capture(2+SLOWDOWN)
            disp( b.save('laser0_%03d.%s'%(n, settings.FILEFORMAT)), 'laser 1')
            b.laser_off(0)
            sleep(0.05)
        if kind & LASER2:
            b.laser_on(1)
            b.wait_capture(2+SLOWDOWN) # sometimes a bit slow to react, so adding one frame
            disp( b.save('laser1_%03d.%s'%(n, settings.FILEFORMAT)) , 'laser 2')
            b.laser_off(1)
            sleep(0.05)
    gui.clear()

def rotate(val):
    """ Rotates the platform by X degrees """
    s = get_scanner()
    if s:
        s.b.motor_move(int(val))

def capture_pattern(t):
    s = get_scanner()
    old_out = s.out
    s.out = settings.CALIBDIR
    s.motor_move(-50)
    sleep(1)
    if not s:
        return
    try:
        scan(s, t, angle=100, definition=3)
        print("")
    except KeyboardInterrupt:
        print("\naborting...")
    s.out = old_out
    s.motor_move(-50)

