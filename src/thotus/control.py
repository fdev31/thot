from time import sleep, time

from thotus.boards import Scanner, get_board
from thotus import settings
from thotus.ui import gui

import numpy as np

COLOR, LASER1, LASER2 = 1, 2, 4 # bit mask
ALL = COLOR | LASER1 | LASER2
SLOWDOWN = 0

scanner = None
lasers = False

def get_camera_controllers():
    s = get_scanner()
    o = {}
    if not s:
        return o
    def _shellwrapper(fn):
        def getsetter(p):
            v = fn(int(p))
            if v:
                print(v)
        return getsetter
    for n in "exposure_absolute brightness gain saturation gain_auto contrast brightness".split():
        o["cam_"+n] = _shellwrapper(getattr(s.cap, "set_"+n))
    return o

def get_scanner():
    global scanner
    if not scanner:
        try:
            scanner = Scanner(out=settings.WORKDIR)
        except RuntimeError as e:
            print("Can't init board: %s"%e.args[0])
        else:
            scanner.refresh_params()
    return scanner

def toggle_interactive_calibration():
    settings.interactive_calibration = not settings.interactive_calibration
    print("Camera calibration set to %s"%("interactive" if settings.interactive_calibration else "automatic"))
    return 3

def toggle_cam_calibration(force_skip=None):
    """ Recompute camera intrinsics (in case you changed the hardware and want a full calibration) """
    if force_skip is not None:
        settings.skip_calibration = force_skip
    else:
        settings.skip_calibration = not settings.skip_calibration

    print("Camera calibration %s"%("disabled" if settings.skip_calibration else "enabled"))
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
    s.current_rotation = 0

    for n in range(angle):
        if definition > 1 and n%definition != 0:
            continue
        gui.progress("scan", n, angle)
        s.motor_move(1*definition)

        t0 = time()
        if on_step:
            on_step()
        t = time() - t0
        sleep(max(0, 0.1 - t)) # wait for motor
        s.wait_capture(2+SLOWDOWN)
        if kind & COLOR:
            disp( s.save('color_%03d.%s'%(n, settings.FILEFORMAT)) , '')
        if kind & LASER1:
            s.laser_on(0)
            s.wait_capture(2+SLOWDOWN)
            disp( s.save('laser0_%03d.%s'%(n, settings.FILEFORMAT)), 'laser 1')
            s.laser_off(0)
            sleep(0.05)
        if kind & LASER2:
            s.laser_on(1)
            s.wait_capture(2+SLOWDOWN) # sometimes a bit slow to react, so adding one frame
            disp( s.save('laser1_%03d.%s'%(n, settings.FILEFORMAT)) , 'laser 2')
            s.laser_off(1)
            sleep(0.05)
    gui.clear()

def rotate(val):
    """ Rotates the platform by X degrees """
    s = get_scanner()
    if s:
        s.motor_move(int(val))

def capture_pattern(t):
    s = get_scanner()
    s.current_rotation = 0
    old_out = s.out
    s.out = settings.CALIBDIR
    s.motor_move(-50)
    sleep(0.7)
    if not s:
        return
    try:
        scan(s, t, angle=100, definition=3)
        print("")
    except KeyboardInterrupt:
        print("\naborting...")
    s.out = old_out
    s.reset_motor_rotation()
