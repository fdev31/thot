from __future__ import print_function

BBOX_MIN = 300
BBOX_MAX = 2000

import math

import cv2
import numpy as np
import scipy.ndimage

from thotus.algorithms.utils import ransac, sgf, find_lines
from thotus.algorithms import algo_pureimage
from thotus.algorithms import algo_straightpureimage

METHOD = 'sgf' # refinement method: sgf, ransac or None


class LineMaker:
    points = None

    def __getattr__(self, name):
        if name.startswith('from_'):
            realname = name[5:]
            mod = globals()['algo_'+realname]
            setattr(self, name, mod.compute)
            return getattr(self, name)
        raise

