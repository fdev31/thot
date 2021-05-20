import os
import sys
import asyncio
import traceback
from time import time
from asyncio import CancelledError

import numpy as np

import prompt_toolkit
from prompt_toolkit.completion import WordCompleter

from thotus.task import Task, GuiFeedback, run_in_thread
from thotus.shell_commands import commands, toggle_advanced_mode
from thotus.commands import get_scanner
from thotus.cloudify import LineMaker
from thotus.calibration.chessboard import chess_detect, chess_draw
from thotus.ui import gui
from thotus import settings

DEBUG = os.getenv('DEBUG', False)

def s2h(t):
    if t > 80:
        return "%d min %ds"%divmod(t, 60)
    else:
        return "%.1fs"%t

class MainGUi:
    running = True
    visible = True
    line_mode = False

    async def viewer(self):
        lm = LineMaker()
        try:
            s = get_scanner()
            if s is None:
                raise ValueError()
        except Exception as e:
            print("Unable to init scanner, not starting viewer.")
            self.stop()
            return

        def process_image():
            img = s.cap.get(-1)
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
                gui.display(img, "live", resize=True)
            try:
                await self.wait_interval()
            except CancelledError:
                return

    async def wait_interval(self):
        await asyncio.sleep(1/60 if self.visible else 1)

    async def cli(self):
        script_commands = []
        if len(sys.argv) > 2 and sys.argv[1] == 'exec':
            script_commands.extend(x.strip() for x in ' '.join(sys.argv[2:]).split(','))
            toggle_advanced_mode()
        session = prompt_toolkit.PromptSession()

        while self.running:
            if script_commands:
                text = script_commands.pop(0)
            else:
                try:
                    text = await session.prompt_async(u'Scan> ', completer = WordCompleter(commands, ignore_case=True, match_middle=False))
                except CancelledError:
                    return
                except EOFError:
                    self.stop()
                    return

            start_execution_ts = time()
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
                    else:
                        duration = time() - start_execution_ts
                        if duration > 1:
                            print("Command %s executed in %ds"%(text, s2h(duration)))

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
