import sys
import asyncio
import traceback
from time import time
from asyncio import CancelledError
from concurrent.futures import ThreadPoolExecutor

import numpy as np

import prompt_toolkit
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.eventloop import use_asyncio_event_loop

from thotus.task import Task, GuiFeedback
from thotus.shell_commands import commands, cmds
from thotus.cloudify import LineMaker
from thotus.calibration.chessboard import chess_detect, chess_draw
from thotus.ui import gui
from thotus import settings


DEBUG = True

timers = dict()
use_asyncio_event_loop()
session = prompt_toolkit.PromptSession()
executor = ThreadPoolExecutor(max_workers=3)
loop = asyncio.get_event_loop()

def prompt(*a, **kw):
    return session.prompt(*a, **kw, async_=True)

def run_in_thread(proc, **kw):
    return asyncio.wrap_future(executor.submit(proc, **kw))

class MainGUi:
    running = True
    visible = True
    line_mode = False

    async def viewer(self):
        lm = LineMaker()
        try:
            s = cmds.get_scanner()
            if s is None:
                raise ValueError()
        except Exception as e:
            print("Unable to init scanner, not starting viewer.")
            self.stop()
            return

        def process_image():
            img = s.cap.get(0)
            if settings.ROTATE:
                img = np.ascontiguousarray(np.rot90(img, settings.ROTATE))
            if self.line_mode:
                lineprocessor = getattr(lm, 'from_'+settings.SEGMENTATION_METHOD)
                s.lasers_on()
                laser_image = s.cap.get(1)
                if settings.ROTATE:
                    laser_image = np.ascontiguousarray(np.rot90(laser_image, settings.ROTATE))
                s.lasers_off()
                points, processed = lineprocessor(laser_image, laser_image[:,:,0], img, img[:,:,0])
                if processed is None:
                    pass # img = black picture ??
                else:
                    img = processed
            else:
                grey = img[:,:,1]
                found, corners = chess_detect(grey)
                if found:
                    chess_draw(img, found, corners)
            return img

        while self.running:
            if self.visible:
                img = await run_in_thread(process_image)
                # process display
                gui.display(img, "live", resize=(96*5, 128*5))
            try:
                await self.wait_interval()
            except CancelledError:
                return

    async def wait_interval(self):
        await asyncio.sleep(1/60 if self.visible else 1)

    async def cli(self):
        script_commands = []
        while self.running:
            try:
                text = await prompt(u'Scan> ', completer = WordCompleter(commands, ignore_case=True, match_middle=False))
            except CancelledError:
                return
            except EOFError:
                try:
                    text = await prompt(u'Exit (Y/n) ? ', completer=WordCompleter( ('yes', 'no')))
                except (KeyboardInterrupt, EOFError):
                    self.stop()
                    return
                else:
                    if not text or text.lower()[0] != 'n':
                        self.stop()
                        return

            if self.running:
                if text.strip():
                    orig_text = text
                    if ' ' in text:
                        params = text.split()
                        text = params[0]
                        params = [x.strip() for x in params[1:]]
                    else:
                        params = ()
                    text = text.strip()
                    if text == "exec":
                        script_commands[:] = [x.strip() for x in ' '.join(params).split(',') if x.strip()]
                        continue
                    try:
                        if text == "exit":
                            self.stop()
                            return
                        t = commands[text](*params)
                        if isinstance(t, GuiFeedback):
                            t.run(self)
                        if t != 3:
                            print("")
                    except KeyboardInterrupt:
                        gui.clear()
                        print("\nAborted!")
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

    async def maincoro(self):
        self._cli = self.cli()
        self._viewer = self.viewer()
        self._coro = asyncio.gather(self._cli, self._viewer)
        await self._coro

    def stop(self):
        if not self.running:
            print("App already stopped!")
            traceback.print_exc()
        self.running = False
        self._coro.cancel()
        commands['exit']()

if __name__ == "__main__":
    app = MainGUi()
    try:
        asyncio.get_event_loop().run_until_complete(app.maincoro())
    except CancelledError:
        pass
    except Exception as e:
        traceback.print_exc()
    print("bye")
