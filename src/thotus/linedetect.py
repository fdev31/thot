from __future__ import print_function

BBOX_MIN = 300
BBOX_MAX = 2000

import math
import importlib

import cv2
import numpy as np
import scipy.ndimage

class LineMaker:
    points = None

    registered_algos = {}

    def __getattr__(self, name):
        if name.startswith('from_'):
            realname = name[5:]
            if realname not in self.registered_algos:
                mod = importlib.import_module('thotus.algorithms.algo_%s'%realname)
                setattr(self, name, mod.compute)
            return getattr(self, name)
        raise

