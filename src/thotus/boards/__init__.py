from __future__ import print_function
import os
import subprocess
from time import sleep

import numpy as np

from thotus import settings
from thotus.camera import Camcorder
from thotus.image.workers import ImageSaver

_board = None
_camera = None
_recorder = None

def get_camera():
    global _recorder
    global _camera
    if _camera is None:
        _recorder = Camcorder()
        from thotus.webcams.logitech_c270 import CameraControl
        try:
            _camera = CameraControl(_recorder)
            print("Logitech c270 detected")
        except Exception:
            from thotus.webcams.generic import CameraControl
            _camera = CameraControl(_recorder)
            print("Generic v4l2 camera detected")

    return _recorder, _camera

def get_board():
    global _board
    if _board is None:

        serial_devices = settings.get_serial_list()

        params = {
            'baud_rate': settings.SERIAL_SPEED or 115200,
            'serial_name': settings.SERIAL_DEVICE or (serial_devices[-1] if serial_devices else None)
        }
        try:
            from .ciclop.board import Board
            _board = Board(**params)
            _board.connect()
            print("Ciclop board connected")
        except Exception:
            from .dummy.board import Board
            _board = Board(**params)
            _board.connect()
            print("Using dummy (fake) board")

    return _board

class Scanner:
    def __init__(self, speed=2000, out=os.path.curdir):
        self.cap, self.cap_ctl = get_camera()
        self.b = get_board()
        self.b.lasers_off()
        self.b.motor_enable()
        self.set_speed(speed)
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

    def wait_capture(self, frames=2, minus=0):
        # TODO improve with minus param
        self.cap.get(frames)

    def save(self, filename):
        if not '.' in filename:
            filename += '.' + settings.FILEFORMAT

        img = self.cap.buff
        if settings.ROTATE:
            img = np.rot90(img, settings.ROTATE)
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


