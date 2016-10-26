import pickle
from collections import defaultdict

from thotus import model
from thotus.ui import gui
from thotus import settings
from thotus.mesh import meshify
from thotus.ply import save_scene
from thotus.linedetect import LineMaker

import cv2
import numpy as np

def cloudify(calibration_data, folder, lasers, sequence, pure_images, rotated=False, method=None, camera=False, cylinder=(100, 200)):
    lm = LineMaker()
    lm.calibration_data = calibration_data
    if method is None:
        print("Error, chose a method from:")
        for n in dir(lm):
            if n.startswith('from_'):
                print(" - %s"%n[5:])
        raise ValueError()
    lineprocessor = getattr(lm, 'from_'+method)
    settings.WORKDIR = folder
    # Pointcloudize !!

    sliced_lines = defaultdict(lambda: [None, None])
    color_slices =  defaultdict(lambda: [None, None])
    w, h = None, None

    S_SZ = 10
    CHANNEL = 2
    for i, n in enumerate(sequence):
        to_display = []
        if not pure_images:
            i2 = cv2.imread(settings.WORKDIR+'/color_%03d.png'%n)
            if i2 is None:
                continue
            i2 = calibration_data.undistort_image(i2)
            i2 = cv2.cvtColor(i2, cv2.COLOR_RGB2HSV)
            i2 = i2[:,:,CHANNEL]
        for laser in lasers:
            diff = cv2.imread(settings.WORKDIR+'/laser%d_%03d.png'%(laser, n))
            hsv = cv2.cvtColor(diff, cv2.COLOR_RGB2HSV)[:,:,CHANNEL]
            if diff is None:
                continue
            if w is None:
                w, h  = hsv.shape
                calibration_data.width = w
                calibration_data.height = h
                calibration_data._compute_weight_matrix()

            hsv = calibration_data.undistort_image(hsv)

            if not pure_images:
                diff = cv2.subtract(hsv, i2)

            blur = cv2.GaussianBlur(diff,(5,5),0)
            val = int(cv2.mean(blur)[0]+0.5)
            diff = cv2.subtract(blur, val*10)

            if not rotated:
                diff = np.rot90(diff, 3)

            gui.progress("analyse", i, len(sequence))

            if camera:
                points = camera[i]['chess_contour']
                mask = np.zeros(diff.shape, np.uint8)

                cv2.fillConvexPoly(mask, points, 255)
                diff = cv2.bitwise_and(diff, diff, mask=mask)

            processed = lineprocessor(diff, laser)
            disp = cv2.merge( np.array((diff, processed, processed)) )
            gui.display(disp, "laser %d"%(laser+1), resize=(640, 480))
            if lm.points and lm.points[0].size:
                if camera:
                    sliced_lines[n][laser] = [ lm.points ] + camera[i]['plane']
                else:
                    sliced_lines[n][laser] = [ np.deg2rad(n), lm.points, laser ]
                    if not pure_images:
                        color_slices[n][laser] = i2[lm.points]

    pickle.dump(dict(sliced_lines), open('lines2d.pyk', 'wb+'))
    return meshify(calibration_data, sliced_lines, camera, cylinder=cylinder)

