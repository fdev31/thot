import pickle
import cv2
import numpy as np
from thotus import model
from thotus.projection import PointCloudGeneration
from thotus.linedetect import LineMaker
from thotus.ply import save_scene
from collections import defaultdict
from thotus.ui import gui

class Mesh:
    def __init__(self):
        self.obj = model.Model(None, is_point_cloud=True)
        self.obj._add_mesh()
        self.obj._mesh._prepare_vertex_count(4000000)

    def get(self):
        return self.obj

    def append_point(self, point, radius=100, height=100):
        color = (50, 180, 180)  # TODO: :(
        obj = self.obj
        rho = np.abs(np.sqrt(np.square(point[0, :]) + np.square(point[1, :])))
        z = point[2, :]

        idx = np.where((z >= 0) &
                       (z <= height) &
                       (rho < radius))[0]

        for i in idx:
            obj._mesh._add_vertex(
                point[0][i], point[1][i], point[2][i],
                color[0], color[1], color[2])
        # Compute Z center
        if point.shape[1] > 0:
            zmax = max(point[2])
            if zmax > obj._size[2]:
                obj._size[2] = zmax

def cloudify(calibration_data, folder, lasers, sequence, pure_images, rotated=False, method=None, camera=False, cylinder=(100, 200)):
    lm = LineMaker()
    if method is None:
        print("Error, chose a method from:")
        for n in dir(lm):
            if n.startswith('from_'):
                print(" - %s"%n[5:])
        raise ValueError()
    lineprocessor = getattr(lm, 'from_'+method)
    WORKDIR = folder
    # Pointcloudize !!

    sliced_lines = defaultdict(lambda: [None, None])
    color_slices =  defaultdict(lambda: [None, None])

    S_SZ = 10
    for i, n in enumerate(sequence):
        to_display = []
        if not pure_images:
            i2 = cv2.imread(WORKDIR+'/color_%03d.png'%n)
            if i2 is None:
                continue
            i2 = calibration_data.undistort_image(i2)
            i2_mean = cv2.mean(i2[0:S_SZ,0:S_SZ])[0]
        for laser in lasers:
            diff = cv2.imread(WORKDIR+'/laser%d_%03d.png'%(laser, n))
            if diff is None:
                continue
            diff = calibration_data.undistort_image(diff)
            if diff is None:
                print("Unable to load %s"%(WORKDIR+'/laser%d_%03d.png'%(laser, n)))

            if not pure_images:
                diff_mean = cv2.mean(diff[0:S_SZ,0:S_SZ])[0]
                diff = diff - ((diff_mean/i2_mean)*i2)
            if not rotated:
                diff = np.rot90(diff, 3)
            gui.progress("analyse", i, len(sequence))
            grey = diff[:,:,0]
            if camera:
                points = camera[i]['chess_contour']
                mask = np.zeros(grey.shape, np.uint8)

                cv2.fillConvexPoly(mask, points, 255)
                grey = cv2.bitwise_and(grey, grey, mask=mask)

            processed = lineprocessor(grey, laser)
            if lm.points:
                if camera:
                    sliced_lines[n][laser] = [ lm.points ] + camera[i]['plane']
                else:
                    sliced_lines[n][laser] = [ np.deg2rad(n), lm.points, laser ]
                    if not pure_images:
                        color_slices[n][laser] = i2[lm.points]

                diff = np.clip(diff, 0, 50)
                diff[:,:,2] = processed

                to_display.append(diff)
        if len(to_display) > 1:
            gui.display(to_display[0] + to_display[1],"lines", resize=(640, 480), disp_number=laser)
        else:
            gui.display(to_display[0], "lines", resize=(640, 480), disp_number=laser)


    pickle.dump(dict(sliced_lines), open('lines2d.pyk', 'wb+'))
    return meshify(calibration_data, sliced_lines, camera, cylinder=cylinder)

def meshify(calibration_data, lines=None, camera=False, lasers=range(2), cylinder=None):
    pcg = PointCloudGeneration(calibration_data)
    if not lines:
        lines = pickle.load(open('lines2d.pyk', 'rb+'))

    obj = Mesh()
    computer = pcg.compute_camera_point_cloud if camera else pcg.compute_point_cloud
    for angle, l in lines.items():
        for laser in lasers:
            x = l[laser]
            if x:
                pc = computer(*x)
                if pc is not None:
                    obj.append_point(pc, radius=cylinder[0], height=cylinder[1])
    return obj.get()
