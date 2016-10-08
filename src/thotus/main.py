#!/usr/bin/python2
import traceback

from prompt_toolkit import prompt
from prompt_toolkit.contrib.completers import WordCompleter

from thotus.commands import capture, recognise

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

while not leave_now:
    try:
        text = prompt(u'Scan Bot> ',
                completer = WordCompleter(commands, ignore_case=True, match_middle=True)
                )
    except EOFError:
        break
    if not text.strip():
        continue
    try:
        if commands[text]() != 3:
            print("")
    except Exception as e:
        print("")
        if DEBUG:
            traceback.print_exc()
        else:
            print("Error occured")
