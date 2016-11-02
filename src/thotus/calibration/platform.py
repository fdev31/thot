from thotus.ui import gui
from thotus import settings
from thotus.mesh import Mesh
from thotus.algorithms.projection import PointCloudGeneration, fit_plane, fit_circle

import cv2
import numpy as np

DEBUG = False
ESTIMATED_PLATFORM_TRANSLAT = [-5, 90, 320] # reference

def calibration(calibration_data, calibration_settings):
    x = []
    y = []
    z = []

    buggy_captures = set()
    pattern_points = settings.get_pattern_points()
    if DEBUG:
        out = Mesh()

    pcg = PointCloudGeneration(calibration_data)
    for i, fn in enumerate(calibration_settings):
        gui.progress('Platform calibration', i, len(calibration_settings))
        corners = calibration_settings[fn]['chess_corners']
        try:
            ret, rvecs, tvecs = cv2.solvePnP(pattern_points, corners, calibration_data.camera_matrix, calibration_data.distortion_vector)
        except Exception as e:
            buggy_captures.add(fn)
            print("Error solving %s : %s"%(fn, e))
            ret = None
        if ret:
            pose = (cv2.Rodrigues(rvecs)[0], tvecs, corners)
            R = pose[0]
            t = pose[1].T[0]
            corner = pose[2]
            normal = R.T[2]
            distance = np.dot(normal, t)
            calibration_settings[fn]['plane'] = [distance, normal]
            if corners is not None:
                origin = corners[settings.PATTERN_MATRIX_SIZE[0] * (settings.PATTERN_MATRIX_SIZE[1] - 1)][0]
                origin = np.array([[origin[0]], [origin[1]]])
                t = pcg.compute_camera_point_cloud(origin, distance, normal)
                if t is not None:
                    if DEBUG:
                        out.append_point(t, 10000, 10000)
                    x += [t[0][0]]
                    y += [t[1][0]]
                    z += [t[2][0]]

    if DEBUG:
        out.save('circle.ply')

    if buggy_captures:
        print("\n %d Buggy Captures!"%len(buggy_captures))

    points = np.array((x, y, z)).transpose()

    if points.size > 4:
        # Fitting a plane
        point, normal = fit_plane(points)
        if normal[1] > 0:
            normal = -normal
        # Fitting a circle inside the plane
        center, R, circle = fit_circle(point, normal, points)
        # Get real origin
        t = center - settings.PATTERN_ORIGIN * np.array(normal) # set ground level
        if t is not None:
            if np.linalg.norm(t - ESTIMATED_PLATFORM_TRANSLAT) > 100:
                print("\n\n!!!!!!!! ISNOGOOD !! %s !~= %s\n\n!!!"%(t, ESTIMATED_PLATFORM_TRANSLAT))

            calibration_data.platform_rotation = R
            calibration_data.platform_translation = t
        print("\nPlatform normal: %s"%normal)
    else:
        raise RuntimeError("Calibration failed")
    return buggy_captures
