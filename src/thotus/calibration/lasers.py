from thotus.ui import gui
from thotus import settings
from thotus.ply import save_scene
from thotus.cloudify import meshify, cloudify

import cv2
import numpy as np

try:
    from scipy.sparse import linalg
except ImportError:
    def svd(M):
        return np.linalg.svd(M)[0][:,2]
else:
    def svd(M):
        return linalg.svds(M, k=2)[0]

def find_laser_plane(X):
    n = X.shape[0]
    Xm = X.sum(axis=0) / n
    M = np.array(X - Xm).T
    U = svd(M)
    normal = np.cross(U.T[0], U.T[1])
    if normal[2] < 0:
        normal *= -1

    dist = np.dot(normal, Xm)
    std = np.dot(M.T, normal).std()
    return (dist, normal, std)

def calibration(calibration_data, images, pure_laser=False):
    for laser in range(2):
        selected_planes = []
        ranges = []
        for fn in images:
            num = int(fn.rsplit('/')[-1].split('_')[1].split('.')[0])
            if laser == 0:
                if num > 70:
                    continue
            else:
                if num < 21:
                    continue
            ranges.append(num)
            selected_planes.append(fn)

        im = [METADATA[x] for x in selected_planes]

        assert len(ranges) == len(im)

        slices = cloudify(calibration_data, settings.CALIBDIR, [laser], ranges, pure_images=pure_laser, method='straightpureimage', camera=im) # cylinder in mm
        obj = meshify(calibration_data, slices, im, cylinder=(1000, 1000))

        v = [_ for _ in obj._mesh.vertexes if np.nonzero(_)[0].size]
        dist, normal, std = find_laser_plane(np.array(v))

        calibration_data.laser_planes[laser].normal = normal
        calibration_data.laser_planes[laser].distance = dist
        save_scene("calibration_laser_%d.ply"%laser, obj)
