from collections import defaultdict

from thotus import model
from thotus.ui import gui
from thotus import imtools
from thotus import settings
from thotus.mesh import meshify
from thotus.linedetect import LineMaker

import cv2
import numpy as np

DEBUG = True

def cloudify(*a, **k):
    for _ in iter_cloudify(*a, **k):
        pass
    return _

def iter_cloudify(calibration_data, folder, lasers, sequence, rotated=False, method=None, camera=False, interactive=False, undistort=False):
    pure_images = settings.pure_mode
    lm = LineMaker()
    lineprocessor = getattr(lm, 'from_'+method)
    lm.calibration_data = calibration_data

    sliced_lines = defaultdict(lambda: [None, None])
    color_slices =  defaultdict(lambda: [None, None])

    d_kern = np.ones((3,3),np.uint8)

    calibration_data.width = 1280
    calibration_data.height = 960


    for i, n in enumerate(sequence):
        yield
        if not pure_images:
            fullcolor, ref_grey = imtools.imread(folder+'/color_%03d.%s'%(n, settings.FILEFORMAT), format="full", calibrated=undistort and calibration_data)
            if ref_grey is None:
                continue
            ref_grey = ref_grey[:,:,2]

        pictures_todisplay = []

        for laser in lasers:
            laser_color, laser_grey = imtools.imread(folder+'/laser%d_%03d.%s'%(laser, n, settings.FILEFORMAT), format="full", calibrated=undistort and calibration_data)
            if laser_color is None:
                continue
            laser_grey = laser_grey[:,:,2]

            if not pure_images:
                laser_color = cv2.subtract(laser_grey, ref_grey)

            gui.progress("analyse", i, len(sequence))

            if camera: # mask pattern
                mask = np.zeros(laser_color.shape, np.uint8)
                cv2.fillConvexPoly(mask, camera[i]['chess_contour'], 255)
                laser_color = cv2.bitwise_and(laser_color, laser_color, mask=mask)

            points, processed = lineprocessor(laser_color, laser)

            # validate & store
            if points is not None and points[0].size:
                nosave = False
                if interactive:
                    disp = cv2.merge( np.array(( laser_grey, processed, processed)) )
                    txt = "Esc=NOT OK, Enter=OK"
                    gui.display(disp, txt,  resize=0.7)
                pictures_todisplay.append((processed, laser_grey))
                if interactive:
                    if not gui.ok_cancel(20):
                        nosave = True

                if not interactive or not nosave:
                    if camera:
                        sliced_lines[n][laser] = [ points ] + camera[i]['plane']
                    else:
                        sliced_lines[n][laser] = [ np.deg2rad(n), points, laser ]
                        if not pure_images:
                            color_slices[n][laser] = fullcolor[(points[1], points[0])]

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

                gui.display(disp, "lasers" if len(lasers) > 1 else "laser %d"%lasers[0],  resize=0.7)
            else:
                if len(pictures_todisplay) > 1:
                    gui.display(cv2.addWeighted(pictures_todisplay[1][1], 0.5, pictures_todisplay[0][1], 0.5, 0), "lasers" if len(lasers) > 1 else "laser %d"%lasers[0],  resize=0.7)
                else:
                    gui.display(pictures_todisplay[0][1], "lasers" if len(lasers) > 1 else "laser %d"%lasers[0],  resize=0.7)
    if camera:
        yield sliced_lines
    else:
        yield sliced_lines, color_slices

