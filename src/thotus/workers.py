from __future__ import print_function

import os
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
    starving = 10
    def stop():
        running = False

    def run(self):

        while self.running:
            try:
                img, path = self.q.get(block=True, timeout=3)
            except Empty:
                self.starving -= 1
            else:
                cv2.imwrite(os.path.join(self.out, path), img)
            if self.starving < 0:
                self.running = False
        print("Writer starved, leaving...")
