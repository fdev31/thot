import cv2
import numpy as np
from thotus import model
from thotus.projection import PointCloudGeneration
from thotus.linedetect import LineMaker
from thotus.ply import save_scene
from collections import defaultdict
from thotus.ui import gui

METHODS = ('pureimage', 'lineimage', 'image')

def cloudify(calibration_data, folder, lasers, sequence, pure_images, rotated=False, method=None):
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
        point = point / 1000.0
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

    pcg = PointCloudGeneration(calibration_data)

    sliced_lines = defaultdict(lambda: [None, None])

    if pure_images:
        for laser in lasers:
            for n in sequence:
                diff = calibration_data.undistort_image(cv2.imread(WORKDIR+'/laser%d_%03d.png'%(laser, n)))
                if not rotated:
                    diff = np.rot90(diff, 3)
                processed = lineprocessor(diff[:,:,0], laser)
                gui.progress("analyse", n, 360)
                if lm.points:
                    sliced_lines[n][laser] = (
                        np.deg2rad(n),
                        lm.points,
                        laser
                    )
                diff[:,:,1] = processed
                diff = diff * 10
                img = diff[200:-100,:].copy()
                gui.display(img,"laser %d"%laser)

    else:
        for n in sequence:
            i2 = calibration_data.undistort_image(cv2.imread(WORKDIR+'/color_%03d.png'%n))
            lsr_img = []
            for laser in lasers:
                i1 = calibration_data.undistort_image(cv2.imread(WORKDIR+'/laser%d_%03d.png'%(laser, n)))
                diff = cv2.absdiff(i1, i2)
                if not rotated:
                    diff = np.rot90(diff, 3)
                processed = lineprocessor(diff[:,:,0], laser)
                gui.progress("analyse", n, 360)

                # project 3D point

                if lm.points:
                    sliced_lines[n][laser] = ( np.deg2rad(n), lm.points, laser)

                # now transform for display
                diff[:,:,1] = processed
                gui.display(diff[200:-100,:].copy(), 'diff')

    for angle, l in sliced_lines.items():
        for laser in lasers:
            pc = pcg.compute_point_cloud(*l[laser])
            if pc is not None:
                append_point(pc)

    return obj
