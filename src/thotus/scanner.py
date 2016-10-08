from __future__ import print_function
import os
import subprocess
from time import sleep


from thotus.board import Board
from thotus.capture import Camcorder
from thotus.workers import ImageSaver

class Scanner:
    writer_t = ImageSaver()

    def __init__(self, speed=2000, out=os.path.curdir):
        self.cap = Camcorder()
        self.b = Board()
        self.b.connect()
        self.b.lasers_off()
        self.b.motor_enable()
        self.set_speed(speed)
        self.writer_t.out = out
        self.writer_t.start()

        def ctl(param, val=None):
            try:
                p = ['uvcdynctrl', '-d', self.cap.dev]
                if val:
                    p.extend(['-s', param, str(val)])
                else:
                    p.extend(['-g', param])
                ret = subprocess.check_output(p)
                if not val:
                    return int(ret)
            except Exception as e:
                print("Error calling %s: %s"%(' '.join(param), e))

        ctl('Exposure, Auto', 3)
        # must sleep this number of ms
        ctl('Exposure (Absolute)', 333)
        ctl('Gain', 0)
        ctl('Brightness', 0)
        ctl('Contrast', 16)
        ctl('Saturation', 0)
        ctl('Backlight Compensation', 0)
        self.exposure = ctl('Exposure (Absolute)')
        if not self.exposure:
            self.exposure = 333
        print("Exposure: %s"%self.exposure)
        self.cap.start()

    def __getattr__(self, name):
        return getattr(self.b, name)

    def set_speed(self, speed):
        self.b.motor_speed(speed/10)
        self.b.motor_acceleration(speed/10)

    @property
    def frame_interval(self):
        return max(2/15.0, self.exposure/10000.0)

    def wait_capture(self, frames=2):
        sleep(self.frame_interval * frames)

    def save(self, filename):
        if not '.' in filename:
            filename += '.png'

        img = self.cap.get()
        self.writer_t.q.put( (img, filename) )
        return img

    def close(self):
        self.writer_t.stop()
        self.cap.stop()
        self.b.lasers_off()
        self.b.motor_disable()

