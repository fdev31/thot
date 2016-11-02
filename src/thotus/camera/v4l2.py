from __future__ import print_function

import glob
import select
from time import sleep
from threading import Thread, Semaphore

import numpy as np
import cv2

try:
    import v4l2capture
except ImportError:
    import thotus.v4l2capture_alt as v4l2capture

MAX_WIDTH=1280
MAX_HEIGHT=960

definition = 1 # 1= highest quality


class Camcorder(Thread):
    YUV = 0
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
        size_x, size_y = video.set_format(width, height, self.YUV, fourcc='I')
        self.size = (size_x, size_y)
        self.ppf = np.multiply(*self.size) # pixels per frame
        self.fps = video.set_fps(30)
        self.sem = None

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
                sleep(0.2)
            except BlockingIOError:
                import traceback
                traceback.print_exc()
                sleep(0.2)
        else:
            raise RuntimeError("Can't init camera")
        print("ready!")

    def __getattr__(self, name):
        return getattr(self.video, name)

    def set_exposure_absolute(self, val):
        self.exposure = self.video.set_exposure_absolute(val)
        return self.exposure

    def stop(self):
        self.terminate = True

    def get(self, frame_nr=1):
        """ Get next `frame_nr` frame """
        self.sem = Semaphore(0)
        for n in range(frame_nr):
            self.sem.acquire()
        self.sem = None
        return self.buff

    def _cap(self):
        sem = self.sem
        image_data = self.video.read_and_queue()
        buff = np.fromstring(image_data, dtype=np.uint8)
        if self.YUV:
            self.buff = buff[:self.ppf].reshape(*reversed(self.size))
        else:
            s = list(reversed(self.size))
            s.append(-1)
            self.buff = cv2.cvtColor(buff.reshape(*s), cv2.COLOR_RGB2BGR)
        if sem:
            self.sem.release()

    def run(self):
        # Start the device. This lights the LED if it's a camera that has one.
        print("Starting capture")
        size_x, size_y = self.size

        while not self.terminate:
            select.select((self.video,), (), ())
            for n in range(10):
                try:
                    self._cap()
                    break
                except BlockingIOError:
                    sleep(0.01)
                    pass
            else:
                print("failed")

        self.video.close()

