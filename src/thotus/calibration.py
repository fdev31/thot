import os
import sys
import json
import math
import pickle
from glob import glob
from collections import defaultdict

from thotus.ui import gui
from thotus.projection import CalibrationData, PointCloudGeneration, clean_model, fit_plane, fit_circle
from thotus.cloudify import cloudify
from thotus.ply import save_scene
from thotus import settings

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

SKIP_CAM_CALIBRATION = 1
FAST_CALIBRATE = 1 # 1 for full calibration, > 1 for grosser calibration

PATTERN_MATRIX_SIZE = (11, 6)
PATTERN_SQUARE_SIZE = 13.0
PATTERN_ORIGIN = 38.8 # distance plateau to second row of pattern
ESTIMATED_PLATFORM_TRANSLAT = [-5, 90, 320] # reference

pattern_points = np.zeros((np.prod(PATTERN_MATRIX_SIZE), 3), np.float32)
pattern_points[:, :2] = np.indices(PATTERN_MATRIX_SIZE).T.reshape(-1, 2)

m_pattern_points = np.multiply(pattern_points, PATTERN_SQUARE_SIZE)

METADATA = defaultdict(lambda: {})

def _view_matrix(m):
    m = repr(m)[5:]
    m = m[1:1+m.rindex(']')]
    return str(eval(m))


def detectChessBoard(img):
    flags = cv2.CALIB_CB_FAST_CHECK
    term = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 200, 0.001)

    found, corners = cv2.findChessboardCorners(img, PATTERN_MATRIX_SIZE, flags=flags)
    if found:
        cv2.cornerSubPix(img, corners, (11, 11), (-1, -1), term)
    return found, corners

def drawChessBoard(img, found, corners):
    try:
        cv2.drawChessboardCorners(img, PATTERN_MATRIX_SIZE, corners, found)
    except TypeError:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        cv2.drawChessboardCorners(img, PATTERN_MATRIX_SIZE, corners, found)
    return img

def lasers_calibration(calibration_data, images, pure_laser=False):

    def compute_pc(X):
        # Load point cloud

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

        obj = cloudify(calibration_data, settings.CALIBDIR, [laser], ranges, pure_images=pure_laser, method='straightpureimage', camera=im, cylinder=(1000, 1000)) # cylinder in mm

        tris = []
        v = [_ for _ in obj._mesh.vertexes if np.nonzero(_)[0].size]
        dist, normal, std = compute_pc(np.array(v))

        if laser == 0:
            name = 'left'
        else:
            name = 'right'

        calibration_data.laser_planes[laser].normal = normal
        calibration_data.laser_planes[laser].distance = dist
        print("laser %d:"%laser)
        print("Normal vector    %s"%(_view_matrix(normal)))
        print("Plane distance    %.4f mm"%(dist))

        save_scene("calibration_laser_%d.ply"%laser, obj)

def platform_calibration(calibration_data):
    x = []
    y = []
    z = []

    buggy_captures = set()

    pcg = PointCloudGeneration(calibration_data)
    for i, fn in enumerate(METADATA):
        gui.progress('Platform calibration', i, len(METADATA))
        corners = METADATA[fn]['chess_corners']
        try:
            ret, rvecs, tvecs = cv2.solvePnP(m_pattern_points, corners, calibration_data.camera_matrix, calibration_data.distortion_vector)
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
            METADATA[fn]['plane'] = [distance, normal]
            if corners is not None:
                origin = corners[PATTERN_MATRIX_SIZE[0] * (PATTERN_MATRIX_SIZE[1] - 1)][0]
                origin = np.array([[origin[0]], [origin[1]]])
                t = pcg.compute_camera_point_cloud(origin, distance, normal)
                if t is not None:
                    x += [t[0][0]]
                    y += [t[1][0]]
                    z += [t[2][0]]

    print("\nBuggy Captures: %d"%len(buggy_captures))
    points = np.array(list(zip(x, y, z)))

    if points.size > 4:
        # Fitting a plane
        point, normal = fit_plane(points)
        if normal[1] > 0:
            normal = -normal
        # Fitting a circle inside the plane
        center, R, circle = fit_circle(point, normal, points)
        # Get real origin
        t = center - PATTERN_ORIGIN * np.array(normal)
        if t is not None:

            print("Platform calibration ")
            print(" Translation: " , _view_matrix(t))
            print(" Rotation: " , _view_matrix(R))
            if np.linalg.norm(t - ESTIMATED_PLATFORM_TRANSLAT) > 100:
                print("\n\n!!!!!!!! ISNOGOOD !! %s !~= %s"%(t, ESTIMATED_PLATFORM_TRANSLAT))

            calibration_data.platform_rotation = R
            calibration_data.platform_translation = t
    else:
        print(":((")
    return buggy_captures

def webcam_calibration(calibration_data, images):
    obj_points = []
    img_points = []
    found_nr = 0

    failed_serie = 0
    term = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, 30, 0.001)
    flags = cv2.CALIB_CB_FAST_CHECK

    for idx, fn in enumerate(images):
        gui.progress('Webcam calibration %s (%d found)... ' % (fn, found_nr), idx, len(images))
        img = cv2.imread(fn, 0)
        # rotation:
        img = cv2.flip(cv2.transpose(img), 1)

        if img is None:
            print("Failed to load", fn)
            continue

        w, h = img.shape[:2]

        found, corners = cv2.findChessboardCorners(img, PATTERN_MATRIX_SIZE, flags=flags)

        if not found:
            if found_nr > 20 and failed_serie > 6:
                break
            failed_serie += 1
            continue

        if flags & cv2.CALIB_CB_FAST_CHECK:
            flags -= cv2.CALIB_CB_FAST_CHECK

        failed_serie = 0
        found_nr += 1
        cv2.cornerSubPix(img, corners, (11, 11), (-1, -1), term)

        METADATA[fn]['chess_corners'] = corners
        img_points.append(corners.reshape(-1, 2))
        obj_points.append(m_pattern_points)

        # compute mask
        p1 = corners[0][0]
        p2 = corners[PATTERN_MATRIX_SIZE[0] - 1][0]
        p3 = corners[PATTERN_MATRIX_SIZE[0] * (PATTERN_MATRIX_SIZE[1] - 1)][0]
        p4 = corners[PATTERN_MATRIX_SIZE[0] * PATTERN_MATRIX_SIZE[1] - 1][0]
        points = np.array([p1, p2, p4, p3], dtype='int32')
        METADATA[fn]['chess_contour'] = points

        vis = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        cv2.drawChessboardCorners(vis, PATTERN_MATRIX_SIZE, corners, found)
        gui.display(vis[int(vis.shape[0]/3):-100,], 'chess')

    if SKIP_CAM_CALIBRATION:
        settings.load_data(calibration_data)
        return

    if not obj_points:
        raise ValueError("Unable to detect pattern on screen :(")
    print("\nComputing calibration...")
    rms, camera_matrix, dist_coefs, rvecs, tvecs = cv2.calibrateCamera(np.array(obj_points), np.array(img_points), (w, h), None, None)

    camera_matrix, roi = cv2.getOptimalNewCameraMatrix(camera_matrix, dist_coefs, (w, h), 1, (w,h))

    calibration_data.camera_matrix = camera_matrix
    calibration_data.distortion_vector = dist_coefs.ravel()

    print("camera matrix:\n%s"% _view_matrix(camera_matrix))
    print("distortion coefficients: %s"% _view_matrix(dist_coefs))
    print("ROI: %s"%(repr(roi)))

def calibrate(pure_laser=False):
    " Compute calibration data from images "

    calibration_data = CalibrationData()

    img_mask = settings.CALIBDIR + '/color_*.' + settings.FILEFORMAT
    img_names = sorted(glob(img_mask))[::FAST_CALIBRATE]

    webcam_calibration(calibration_data, img_names)
    buggy_captures = platform_calibration(calibration_data)

    good_images = set(METADATA)
    good_images.difference_update(buggy_captures)
    good_images = list(good_images)
    good_images.sort()
    pickle.dump(dict(
            images = good_images,
            metadata = dict(METADATA),
            )
            , open('images.js', 'wb'))

    lasers_calibration(calibration_data, good_images, pure_laser)
    settings.save_data(calibration_data)
    METADATA.clear()
    gui.clear()
