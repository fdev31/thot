#!/usr/bin/python2
import traceback
import sys
from time import time

from prompt_toolkit import prompt
from prompt_toolkit.contrib.completers import WordCompleter
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.token import Token
from prompt_toolkit.styles import style_from_dict

from thotus import commands as cmds
from thotus import settings
from thotus.ui import gui
history = InMemoryHistory()

def s2h(t):
    if t > 80:
        return "%d min %ds"%divmod(t, 60)
    else:
        return "%.1fs"%t

def get_bottom_toolbar_tokens(cli):
    if not timers:
        txt = ' Welcome!'
    else:
        txt = "Last command executed in %s"%(s2h(timers['end_execution']-timers['execution']))
    return [(Token.Toolbar, txt)]

style = style_from_dict({
    Token.Toolbar: '#ffffff bg:#333333',
})

leave_now = False
DEBUG = True

def exit():
    global leave_now
    leave_now = True
    return 3

def help():
    print("Commands:")
    for c in commands:
        print(" - %s"%c)
    return 3

def set_horus_cfg():
    settings.configuration = 'horus'

def set_thot_cfg():
    settings.configuration = 'thot'

def set_single_laser(laser_number):
    i = int(laser_number)
    if i not in (1, 2):
        print("Laser number must be 1 or 2")
    settings.single_laser = i-1

def set_dual_laser():
    settings.single_laser = None

def scan():
    cmds.capture_color()
    cmds.capture_lasers()
    return cmds.recognize()

commands = dict(
        debug_settings = settings.compare,
        # calibrate
        calibrate      = cmds.calibrate,
        calibrate_cam  = cmds.toggle_cam_calibration,

        # all in one scan
        scan           = scan,
        # acquire pictures
        capture        = cmds.capture,
        capture_color  = cmds.capture_color,
        capture_lasers = cmds.capture_lasers,
        pattern_colors = cmds.capture_pattern_colors,
        pattern_lasers = cmds.capture_pattern_lasers,


        # scan
        analyse        = cmds.recognize,
        analyse_pure   = cmds.recognize_pure,

        # misc
        view           = cmds.view,
        rotate         = cmds.rotate,
        lasers         = cmds.switch_lasers,
        exit           = exit,
        quit           = exit,
        help           = help,
        use_horus_cfg  = set_horus_cfg,
        use_thot_cfg   = set_thot_cfg,
        set_single_laser = set_single_laser,
        set_dual_laser = set_dual_laser,
    )

try:
    commands.update(cmds.get_controllers())
except IndexError:
    print("Unable to find camera, is it plugged ?")

timers = dict()

def wanna_leave():
    global leave_now
    print("Aborted !")
    try:
        text = prompt(u'Exit (Y/n) ? ', completer=WordCompleter( ('yes', 'no') , ignore_case=True
        ))
    except (KeyboardInterrupt, EOFError):
        leave_now = True
    else:
        if not text or text.lower()[0] != 'n':
            leave_now = True

leave_after = False
if len(sys.argv) > 1:
    text = ' '.join(sys.argv[1:])
    sys.argv[:] = [sys.argv[0]]
    leave_after = True

while not leave_now:
    if not leave_after:
        try:
            text = prompt(u'Scan Bot> ',
                    history=history,
                    get_bottom_toolbar_tokens=get_bottom_toolbar_tokens,
                    style=style,
                    completer = WordCompleter(commands, ignore_case=True, match_middle=False,
                        )
                    )
        except EOFError:
            break
        except KeyboardInterrupt:
            wanna_leave()

    if leave_now:
        break

    timers['execution'] = time()
    if text.strip():
        if ' ' in text:
            params = text.split()
            text = params[0]
            params = params[1:]
        else:
            params = ()
        try:
            if commands[text](*params) != 3:
                print("")
        except KeyboardInterrupt:
            gui.clear()
            wanna_leave()
        except KeyError:
            print("Command not found: %s"%text)
        except Exception as e:
            gui.clear()
            print("")
            if DEBUG:
                traceback.print_exc()
            else:
                print("Error occured")
    timers['end_execution'] = time()
    if leave_after:
        leave_now = True

cmds.stop()
