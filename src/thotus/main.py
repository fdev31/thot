#!/usr/bin/python2
import traceback

from prompt_toolkit import prompt
from prompt_toolkit.contrib.completers import WordCompleter

from thotus.commands import capture, recognise
from thotus.ui import gui

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

commands = dict(capture=capture, analyse=recognise, exit=exit, help=help)

def wanna_leave():
    print("Aborted !")
    try:
        text = prompt(u'Exit (Y/n) ? ', completer=WordCompleter( ('yes', 'no') , ignore_case=True))
    except KeyboardInterrupt:
        raise SystemExit(0)
    else:
        if text.lower()[0] != 'n':
            raise SystemExit(0)

while not leave_now:
    try:
        text = prompt(u'Scan Bot> ',
                completer = WordCompleter(commands, ignore_case=True, match_middle=True)
                )
    except EOFError:
        break
    except KeyboardInterrupt:
        wanna_leave()

    if text.strip():
        try:
            if commands[text]() != 3:
                print("")
        except KeyboardInterrupt:
            wanna_leave()
        except Exception as e:
            print("")
            if DEBUG:
                traceback.print_exc()
            else:
                print("Error occured")
    gui.clear()
