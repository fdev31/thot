import cv2
import numpy as np
from thotus import model
from thotus.projection import PointCloudGeneration
from thotus.linedetect import LineMaker
from thotus.ply import save_scene
from collections import defaultdict
from thotus.ui import gui

METHODS = ('pureimage', 'lineimage', 'image', 'simpleline')

def cloudify(calibration_data, folder, lasers, sequence, pure_images, rotated=False, method=None, camera=False):
    lm = LineMaker()
    if method is None:
        method = METHODS[0]
    lineprocessor = getattr(lm, 'from_'+method)
    WORKDIR = folder
    # Pointcloudize !!
    obj = model.Model(None, is_point_cloud=True)
    obj._add_mesh()
    obj._mesh._prepare_vertex_count(4000000)

    color = (50, 180, 180)

    def append_point(point, radius=0.1, height=15):
        rho = np.abs(np.sqrt(np.square(point[0, :]) + np.square(point[1, :])))
        z = point[2, :]

        idx = np.where((z >= 0) &
                       (z <= height) &
                       (rho < radius))[0]

        for i in range(point.shape[1]):
            obj._mesh._add_vertex(
                point[0][i], point[1][i], point[2][i],
                color[0], color[1], color[2])
        # Compute Z center
        if point.shape[1] > 0:
            zmax = max(point[2])
            if zmax > obj._size[2]:
                obj._size[2] = zmax

    pcg = PointCloudGeneration(calibration_data)

    sliced_lines = defaultdict(lambda: [None, None])

    if pure_images:
        for laser in lasers:
            for i, n in enumerate(sequence):
                diff = calibration_data.undistort_image(cv2.imread(WORKDIR+'/laser%d_%03d.png'%(laser, n)))
                if not rotated:
                    diff = np.rot90(diff, 3)
                processed = lineprocessor(diff[:,:,0], laser)
                gui.progress("analyse", i, len(sequence))
                if lm.points:
                    if camera:
                        sliced_lines[n][laser] = [ lm.points ] + camera[i]['plane']
                    else:
                        sliced_lines[n][laser] = [ np.deg2rad(n), lm.points, laser ]
                gui.display(processed,"laser %d"%laser, resize=(640, 480))

    else:
        for i, n in enumerate(sequence):
            i2 = calibration_data.undistort_image(cv2.imread(WORKDIR+'/color_%03d.png'%n))
            lsr_img = []
            for laser in lasers:
                i1 = calibration_data.undistort_image(cv2.imread(WORKDIR+'/laser%d_%03d.png'%(laser, n)))
                diff = cv2.absdiff(i1, i2)
                if not rotated:
                    diff = np.rot90(diff, 3)
                processed = lineprocessor(diff[:,:,0], laser)
                gui.progress("analyse", n, len(sequence))

                # project 3D point

                if lm.points:
                    if camera:
                        sliced_lines[n][laser] = [ lm.points ] + camera[i]['plane']
                    else:
                        sliced_lines[n][laser] = [ np.deg2rad(n), lm.points, laser ]

                gui.display(processed, 'diff', resize=(640, 480))


    if camera:
        computer = pcg.compute_camera_point_cloud
        for angle, l in sliced_lines.items():
            for laser in lasers:
                try:
                    pc = computer(*l[laser])
                except Exception as e:
                    print("Err: %s"%e)
                else:
                    if pc is not None:
                        append_point(pc/1000.0)
    else:
        pu.db
        computer = pcg.compute_point_cloud
        for angle, l in sliced_lines.items():
            for laser in lasers:
                x = l[laser]
                if x:
                    pc = computer(*x)
                    if pc is not None:
                        append_point(pc/1000.0)


    return obj
