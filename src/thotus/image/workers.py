import os
from time import sleep
from threading import Thread
try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty

import cv2

from thotus.ui import gui

class ImageSaver(Thread):

    q = Queue(maxsize=200)
    running = True

    def __init__(self, out_dir):
        Thread.__init__(self)
        self.out=out_dir

    def stop(self):
        self.running = False

    def run(self):

        while self.running:
            try:
                r = self.q.get(block=True, timeout=3)
                try:
                    if len(r) > 2:
                        img = r[2](r[0])
                        path = r[1]
                    else:
                        img, path = r
                except:
                    img, path = r
            except Empty:
                sleep(0.5)
            else:
                cv2.imwrite(os.path.join(self.out, path), img)

