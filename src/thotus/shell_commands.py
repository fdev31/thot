import sys
import traceback
from time import time, sleep
from threading import Thread

from thotus.ui import gui
from thotus.task import Task
from thotus import settings
from thotus import commands as cmds

def exit():
    cmds.get_scanner().close()
    return 3

def help():
    print("Commands:")
    for c in sorted(commands):
        if c.startswith('cam_'):
            d = 'get or set camera %s'%c[4:].strip()
        else:
            d = commands[c].__doc__
        if d:
            d = d.strip().title()
        else:
            d = ""
        print(" %-20s  %s"%(c, d.title()))
    return 3

def toggle_advanced_mode():
    """ toggle advanced command set """
    if 'debug_settings' in commands:
        for cmd in adv_commands:
            del commands[cmd]
        print("Using simple commands")
    else:
        commands.update(adv_commands)
        print("Using advanced commands")
    return 3

def cmd_sleep(delay):
    sleep(float(delay))
    return 3

def calibrate_manual():
    """ Calibrate platform & scanner with user confirmation of laser lines """
    return  cmds.stdcalibrate(True)

def recalibrate_manual():
    """ Calibrate platform & scanner with user confirmation of laser lines """
    return  cmds.calibrate(True)


commands = dict(
    # calibrate
    calibrate      = cmds.stdcalibrate,
    advanced       = toggle_advanced_mode,

    # when it's not working...
    calibrate_manual  = calibrate_manual,

    # all in one scan
    scan           = cmds.scan_object,

    # misc
    view           = cmds.view,
    rotate         = cmds.rotate,
    lasers         = cmds.switch_lasers,
    exit           = exit,
    quit           = exit,
    help           = help,
    keep_laser     = cmds.set_single_laser,
    roi            = cmds.set_roi,
    )

adv_commands = dict(
    wait =  lambda: 3,
    sleep          = cmd_sleep,
    pattern_colors   = cmds.capture_pattern_colors,
    pattern_lasers   = cmds.capture_pattern_lasers,
    cfg            = cmds.set_cfg,
    algorithm      = cmds.set_algorithm,
    algop          = cmds.set_algo_value,
    debug_settings = settings.compare,
    import_val     = settings.import_val,
    view_mode      = cmds.view_mode,
    # take calibration data
    shot           = cmds.shot,
    shots_remove   = cmds.shots_clear,
    calibrate_shots= cmds.calibrate_cam_from_shots,

    # compute calibration data
    recalibrate      = cmds.calibrate,
    recalibrate_manual  = recalibrate_manual,

    # acquire pictures
    capture          = cmds.capture,
    capture_color    = cmds.capture_color,
    capture_lasers   = cmds.capture_lasers,

    # pure mode
    pure = cmds.toggle_pure_mode,

    # build 3D mesh
    make          = cmds.recognize,

    use_horus_cfg    = cmds.set_horus_cfg,
    use_thot_cfg     = cmds.set_thot_cfg,
)

try:
    commands.update(cmds.get_camera_controllers())
except IndexError:
    print("Unable to find camera, is it plugged ?")

timers = dict()
