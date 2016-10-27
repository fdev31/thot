from collections import defaultdict

from thotus import model
from thotus.ui import gui
from thotus import settings
from thotus.mesh import meshify
from thotus.linedetect import LineMaker

import cv2
import numpy as np

def cloudify(*a, **k):
    for _ in iter_cloudify(*a, **k):
        pass
    return _

def iter_cloudify(calibration_data, folder, lasers, sequence, pure_images, rotated=False, method=None, camera=False, interactive=False):
    lm = LineMaker()
    lm.calibration_data = calibration_data
    if method is None:
        print("Error, chose a method from:")
        for n in dir(lm):
            if n.startswith('from_'):
                print(" - %s"%n[5:])
        raise ValueError()
    lineprocessor = getattr(lm, 'from_'+method)
    # Pointcloudize !!

    sliced_lines = defaultdict(lambda: [None, None])
    color_slices =  defaultdict(lambda: [None, None])
    w, h = None, None

    S_SZ = 10
    CHANNEL = 2
    for i, n in enumerate(sequence):
        yield
        if not pure_images:
            i2 = cv2.imread(folder+'/color_%03d.%s'%(n, settings.FILEFORMAT))
            if i2 is None:
                continue
            i2 = calibration_data.undistort_image(i2)
            fullcolor = cv2.cvtColor(i2, cv2.COLOR_RGB2HSV)
            i2 = fullcolor[:,:,CHANNEL]
        for laser in lasers:
            diff = cv2.imread(folder+'/laser%d_%03d.%s'%(laser, n, settings.FILEFORMAT))
            hsv = cv2.cvtColor(diff, cv2.COLOR_RGB2HSV)[:,:,CHANNEL]
            if diff is None:
                continue
            if w is None:
                w, h  = hsv.shape
                calibration_data.width = w
                calibration_data.height = h

            hsv = calibration_data.undistort_image(hsv)

            if not pure_images:
                diff = cv2.subtract(hsv, i2)

            val = int(cv2.mean(diff)[0]+0.5)
            diff = cv2.subtract(diff, val*10)

            if not rotated:
                diff = np.rot90(diff, 3)

            gui.progress("analyse", i, len(sequence))

            if camera: # mask pattern
                mask = np.zeros(diff.shape, np.uint8)
                cv2.fillConvexPoly(mask, camera[i]['chess_contour'], 255)
                diff = cv2.bitwise_and(diff, diff, mask=mask)

            points, processed = lineprocessor(diff, laser)

            if points is not None and points[0].size:
                nosave = False
                disp = cv2.merge( np.array((np.clip(diff*10, 0, 100), processed, processed)) )
                if interactive:
                    txt = "Esc=NOT OK, Enter=OK"
                else:
                    txt = "laser %d"%(laser+1)
                gui.display(disp, txt,  resize=(640, 640))
                if interactive:
                    for n in range(20):
                        x = cv2.waitKey(100)
                        if x == 27:
                            nosave = True
                            break
                        elif x&0xFF in (10, 32):
                            break

                if not interactive or not nosave:
                    if camera:
                        sliced_lines[n][laser] = [ points ] + camera[i]['plane']
                    else:
                        sliced_lines[n][laser] = [ np.deg2rad(n), points, laser ]
                        if not pure_images:
                            color_slices[n][laser] = i2[points]
    if camera:
        yield sliced_lines
    else:
        yield sliced_lines, color_slices

