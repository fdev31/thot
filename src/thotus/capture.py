from __future__ import print_function

import select
from threading import Thread
from time import sleep

import cv2
import numpy as np
import glob

try:
    import v4l2capture
except ImportError:
    import thotus.v4l2capture_alt as v4l2capture

MAX_WIDTH=1280
MAX_HEIGHT=960

definition = 1 # 1= highest quality


class Camcorder(Thread):
    def __init__(self, width=MAX_WIDTH, height=MAX_HEIGHT):
        if not v4l2capture:
            raise RuntimeError("Can't find v4l2capture")
        Thread.__init__(self)
        self.setDaemon(True)
        # Open the video device.
        try:
            self.dev = glob.glob("/dev/video*")[-1]
        except IndexError:
            raise RuntimeError("Check your webcam device (unplugged ?)")
        video = v4l2capture.Video_device(self.dev)
        # Suggest an image size to the device. The device may choose and
        # return another size if it doesn't support the suggested one.
        size_x, size_y = video.set_format(width, height, 1, fourcc='I')
        self.size = (size_x, size_y)
        self.ppf = np.multiply(*self.size) # pixels per frame
        self.fps = video.set_fps(30)

        video.create_buffers(1)

        video.queue_all_buffers()
        self.video = video
        self.terminate = False
        self.video.start()
        print("Waiting for cam to be ready...")
        for n in range(10):
            try:
                self._cap()
                break
            except Exception as e:
                if not ( e.args and e.args[0] == 11):
                    import traceback
                    traceback.print_exc()
                sleep(1)
        else:
            raise RuntimeError("Can't init camera")

    def __getattr__(self, name):
        return getattr(self.video, name)

    def stop(self):
        self.terminate = True

    def get(self):
        return self.buff

    def _cap(self):
        image_data = self.video.read_and_queue()
        buff = np.fromstring(image_data, dtype=np.uint8)
        self.buff = buff[:self.ppf].reshape(*reversed(self.size))

    def run(self):
        # Start the device. This lights the LED if it's a camera that has one.
        print("Starting capture")
        size_x, size_y = self.size

        while not self.terminate:
            select.select((self.video,), (), ())
            self._cap()

        self.video.close()
        cv2.destroyAllWindows()


