from thotus import settings
from thotus.cloudify import cloudify
from thotus.mesh import meshify

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

def calibration(calibration_data, calibration_settings, images):
    tot_deviation = 0.0
    for laser in settings.get_laser_range():
        selected_planes = []
        ranges = []
        for fn in images:
            num = int(fn.rsplit('/')[-1].split('_')[1].split('.')[0])
            if laser == 0:
                if num > 80:
                    continue
            else:
                if num < 20:
                    continue
            ranges.append(num)
            selected_planes.append(fn)

        im = [calibration_settings[x] for x in selected_planes]

        assert len(ranges) == len(im)

        slices = cloudify(calibration_data, settings.CALIBDIR, [laser], ranges,
                method='straightpureimage', camera=im, interactive=settings.interactive_calibration, undistort=True)

        obj = meshify(calibration_data, slices, camera=im, cylinder=(1000, 1000))

        dist, normal, std = find_laser_plane(np.array(obj.vertices))
        tot_deviation += std
        print("Laser %d deviation: %.2f"%(laser, std))

        calibration_data.laser_planes[laser].normal = normal
        calibration_data.laser_planes[laser].distance = dist
        obj.save("laser%d.ply"%laser)

    if tot_deviation < 0.01:
        txt = ("Excellent !!")
    elif tot_deviation < 0.05:
        txt = ("Good !")
    elif tot_deviation < 0.1:
        txt = ("Not bad ;)")
    elif tot_deviation < 0.3:
        txt = ("Expect shift between lasers")
    else:
        txt = ("Consider recalibrating, result is very bad")

    print("\nDeviation is %.2f. %s"%(tot_deviation, txt))

