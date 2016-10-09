#!/usr/bin/python2
import traceback

from prompt_toolkit import prompt
from prompt_toolkit.contrib.completers import WordCompleter
from prompt_toolkit.history import InMemoryHistory

from thotus.commands import capture, capture_color, capture_lasers, recognize, switch_lasers, view, stop
from thotus.commands import recognize_pure, get_controllers
from thotus.ui import gui
history = InMemoryHistory()


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

commands = dict(
        capture        = capture,
        capture_color  = capture_color,
        capture_lasers = capture_lasers,
        analyse        = recognize,
        parse_lines    = recognize_pure,
        view           = view,
        exit           = exit,
        help           = help,
        lasers         = switch_lasers,
    )

commands.update(get_controllers())

def wanna_leave():
    global leave_now
    print("Aborted !")
    try:
        text = prompt(u'Exit (Y/n) ? ', completer=WordCompleter( ('yes', 'no') , ignore_case=True))
    except KeyboardInterrupt:
        leave_now = True
    else:
        if text.lower()[0] != 'n':
            leave_now = True

while not leave_now:
    try:
        text = prompt(u'Scan Bot> ',
                history=history,
                completer = WordCompleter(commands, ignore_case=True, match_middle=True)
                )
    except EOFError:
        break
    except KeyboardInterrupt:
        wanna_leave()

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
            wanna_leave()
        except Exception as e:
            print("")
            if DEBUG:
                traceback.print_exc()
            else:
                print("Error occured")

stop()
