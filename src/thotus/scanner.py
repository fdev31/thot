from __future__ import print_function
import os
import subprocess
from time import sleep

from thotus.board import Board
from thotus.capture import Camcorder
from thotus.workers import ImageSaver

_board = None

controls = """
Brightness
Contrast
Saturation
#White Balance Temperature, Auto
Gain
#Power Line Frequency
#White Balance Temperature
Sharpness
#Backlight Compensation
#Exposure, Auto
Exposure (Absolute)
#Exposure, Auto Priority
""".strip().split('\n')

def get_board():
    global _board
    if not _board:
        _board = Board()
        try:
            _board.connect()
        except Exception as e:
            raise RuntimeError("Can't connect to board, is it plugged to USB & Powered on ?")
    return _board

def get_controllers():
    import re
    import glob
    from functools import partial
    words = re.compile(r'\W+')
    dev = glob.glob("/dev/video*")[-1]

    functions = {}
    for ctl_name in controls:
        if ctl_name[0] != '#':
            shortname = words.sub('', ctl_name)
            functions["cam_"+shortname] = partial(ctl_param, dev, ctl_name, show=True)
    return functions

def ctl_param(dev, param, val=None, show=False):
    try:
        p = ['uvcdynctrl', '-d', dev]
        if val:
            p.extend(['-s', param, str(val)])
        else:
            p.extend(['-g', param])
        ret = subprocess.check_output(p)
        if not val:
            if show:
                print("%d"%int(ret))
            else:
                return int(ret)
    except Exception as e:
        print("Error calling %s: %s"%(' '.join(param), e))


class Scanner:

    def __init__(self, speed=2000, out=os.path.curdir):
        self.writer_t = ImageSaver(out)
        self.b = get_board()
        self.b.lasers_off()
        self.b.motor_enable()
        self.set_speed(speed)
        self.cap = Camcorder()
        self.writer_t.start()

        print(self.cap.set_exposure_auto(1))
        print(self.cap.set_auto_white_balance(0))
        self.exposure = self.cap.set_exposure_absolute(333)
        ctl_param(self.cap.dev, 'Gain', 255)
        ctl_param(self.cap.dev, 'Brightness', 0)
        ctl_param(self.cap.dev, 'Contrast', 32)
        ctl_param(self.cap.dev, 'Saturation', 20)
        ctl_param(self.cap.dev, 'Backlight Compensation', 0)
        ctl_param(self.cap.dev, 'Exposure, Auto Pirority', 1)
        print("Exposure: %s"%self.exposure)
        self.cap.start()

    def __getattr__(self, name):
        return getattr(self.b, name)

    def refresh_params(self):
        self.exposure = self.cap.get_exposure_absolute()

    def set_speed(self, speed):
        self.b.motor_speed(speed/10)
        self.b.motor_acceleration(speed/10)

    @property
    def frame_interval(self):
        return max(1/self.cap.fps, (self.exposure/5000.0))*1.1

    def wait_capture(self, frames=2, min_val=0.150):
        x = self.frame_interval * frames
        sleep(max(x, min_val))
        return x

    def save(self, filename, processing=None):
        if not '.' in filename:
            filename += '.png'

        img = self.cap.get()
        self.writer_t.q.put( (img, filename) )
        return img

    def close(self):
        print("Closing device...")
        self.b.lasers_off()
        self.b.motor_disable()
        self.writer_t.stop()
        self.cap.stop()
        self.writer_t.join()
        self.cap.join()

