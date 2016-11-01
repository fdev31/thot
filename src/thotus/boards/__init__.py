from __future__ import print_function
import os
import subprocess
from time import sleep

from thotus import settings
from thotus.camera import Camcorder
from thotus.workers import ImageSaver

_board = None

def get_board():
    return _board

class Scanner:
    def __init__(self, speed=2000, out=os.path.curdir):
        self.b = get_board()
        self.b.lasers_off()
        self.b.motor_enable()
        self.set_speed(speed)
        self.cap = Camcorder()
        self.cap_ctl = CameraControl(self.cap)
        self.current_rotation = 0
        self.writer_t = ImageSaver(out)
        self.writer_t.start()

    def g_out(self):
        return self.writer_t.out

    def s_out(self, val):
        self.writer_t.out = val

    out = property(g_out, s_out)

    def __getattr__(self, name):
        return getattr(self.b, name)

    def motor_move(self, value):
        try:
            self.b.motor_move(value)
        except Exception as e:
            print(e)
        else:
            self.current_rotation += value

    def reset_motor_rotation(self):
        v = self.current_rotation % 360
        if v > 180:
            self.motor_move(360-v)
        else:
            self.motor_move(-v)
        self.current_rotation = 0

    def set_speed(self, speed):
        self.b.motor_speed(speed/10)
        self.b.motor_acceleration(speed/10)

    @property
    def frame_interval(self):
        return max(1/self.cap.fps, (self.cap_ctl.exposure/10000.0))*1.1

    def wait_capture(self, frames=2, min_val=0.150, minus=0):
        x = self.frame_interval * frames
        d = max(x, min_val)
        x -= minus
        if x > 0:
            sleep(d)
            return d
        return 0

    def save(self, filename, processing=None):
        if not '.' in filename:
            filename += '.' + settings.FILEFORMAT

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

try:
    from .ciclop.board import Board, CameraControl
    _board = Board()
    _board.connect()
    print("Ciclop board connected")
except Exception:
    from .dummy.board import Board, CameraControl
    _board = Board()
    _board.connect()
    print("Using dummy (fake) board")

