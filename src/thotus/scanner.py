from __future__ import print_function
import os
import subprocess
from time import sleep

from thotus import settings
from thotus.board import Board
from thotus.capture import Camcorder
from thotus.workers import ImageSaver

_board = None

controls = """
brightness
contrast
caturation
gain
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


class Scanner:
    def __init__(self, speed=2000, out=os.path.curdir):
        self.writer_t = ImageSaver(out)
        self.b = get_board()
        self.b.lasers_off()
        self.b.motor_enable()
        self.set_speed(speed)
        self.cap = Camcorder()
        self.writer_t.start()

        self.cap.set_exposure_auto(0)
        self.cap.set_auto_white_balance(0)
        self.cap.set_white_balance_temperature(0)
        self.exposure = self.cap.set_exposure_absolute(333)
        self.cap.set_brightness(0)
        self.cap.set_gain(255)
        self.cap.set_hue_auto(0)
        self.cap.set_hue(0)
        self.cap.set_contrast(32)
        self.cap.set_saturation(20)
        self.cap.start()
        self.current_rotation = 0

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

