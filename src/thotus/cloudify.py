import importlib
from collections import defaultdict

from thotus.ui import gui
from thotus.image import tools as imtools
from thotus import settings

import cv2
import numpy as np

DEBUG = True

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


def cloudify(*a, **k):
    _ = None
    for _ in iter_cloudify(*a, **k):
        pass
    return _

def iter_cloudify(calibration_data, folder, lasers, sequence, method=None, camera=False, interactive=False, undistort=False):
    pure_images = settings.pure_mode
    lm = LineMaker()
    lineprocessor = getattr(lm, 'from_'+method)
    lm.calibration_data = calibration_data

    sliced_lines = defaultdict(lambda: [None, None])
    color_slices =  defaultdict(lambda: [None, None])

    d_kern = np.ones((3,3),np.uint8)

    for i, n in enumerate(sequence):
        yield

        fullcolor = imtools.imread(folder+'/color_%03d.%s'%(n, settings.FILEFORMAT), format="rgb", calibrated=undistort and calibration_data)
        if fullcolor is None:
            continue

        if pure_images:
            ref_grey = None
        else:
            ref_grey = fullcolor[:,:,0]

        pictures_todisplay = []

        for laser in lasers:
            laser_image = imtools.imread(folder+'/laser%d_%03d.%s'%(laser, n, settings.FILEFORMAT), format="rgb", calibrated=undistort and calibration_data)

            if laser_image is None:
                continue

            laser_grey = laser_image[:,:,2]

            gui.progress("analyse", i, len(sequence))
            points, processed = lineprocessor(laser_image, laser_grey, fullcolor, ref_grey, laser_nr=laser,
                    mask=camera[i]['chess_contour'] if camera else None)

            # validate & store
            if points is not None and points[0].size:
                nosave = False
                if interactive:
                    disp = cv2.merge( np.array(( laser_grey, processed, processed)) )
                    txt = "Esc=NOT OK, Enter=OK"
                    gui.display(disp, txt,  resize=True)
                pictures_todisplay.append((processed, laser_grey))
                if interactive:
                    if not gui.ok_cancel(20):
                        nosave = True

                if not interactive or not nosave:
                    if camera:
                        sliced_lines[n][laser] = [ points ] + camera[i]['plane']
                    else:
                        sliced_lines[n][laser] = [ np.deg2rad(n), points, laser ]
                        if fullcolor is not None:
                            color_slices[n][laser] = np.fliplr(fullcolor[(points[1], points[0])])

        # display
        if i%int(settings.ui_base_i*2) == 0 and pictures_todisplay:
            if DEBUG:
                if len(pictures_todisplay) > 1:
                    pictures_todisplay = np.array(pictures_todisplay)
                    gref = cv2.addWeighted(pictures_todisplay[0,1], 0.3, pictures_todisplay[1,1], 0.3, 0)
                    nref = cv2.addWeighted(pictures_todisplay[0,0], 0.5, pictures_todisplay[1,0], 0.5, 0)
                else:
                    gref = pictures_todisplay[0][1]
                    nref = pictures_todisplay[0][0]

                nref = cv2.dilate(nref, d_kern).astype(np.uint8)
                r = cv2.bitwise_or(gref, nref)
                disp = cv2.merge( np.array(( r, gref, r)) )

                gui.display(disp, "lasers" if len(lasers) > 1 else "laser %d"%lasers[0],  resize=True)
            else:
                if len(pictures_todisplay) > 1:
                    gui.display(cv2.addWeighted(pictures_todisplay[1][1], 0.5, pictures_todisplay[0][1], 0.5, 0), "lasers" if len(lasers) > 1 else "laser %d"%lasers[0],  resize=True)
                else:
                    gui.display(pictures_todisplay[0][1], "lasers" if len(lasers) > 1 else "laser %d"%lasers[0],  resize=True)
        else:
            gui.redraw()
    if len(sliced_lines) == 0:
        return None
    if camera:
        yield sliced_lines
    else:
        yield sliced_lines, color_slices

