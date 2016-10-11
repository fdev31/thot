import os
import sys
import json
import math
import pickle
from glob import glob
from collections import defaultdict

SKIP_CAM_CALIBRATION = 0
from thotus.ui import gui
from thotus.projection import CalibrationData, PointCloudGeneration, clean_model, fit_plane, fit_circle
from thotus.linedetect import LineMaker, compute_plane
from thotus.cloudify import cloudify
from thotus.ply import save_scene

import cv2
import numpy as np
from scipy.sparse import linalg

PATTERN_MATRIX_SIZE = (11, 6)
PATTERN_SQUARE_SIZE = 13.0
PATTERN_ORIGIN = 38.88 # distance plateau to second row of pattern
ESTIMATED_PLATFORM_TRANSLAT = [-5, 90, 320] # reference 

COLLECTED_SETTINGS = {}
METADATA = defaultdict(lambda: {})

def load_data():
    global COLLECTED_SETTINGS
    COLLECTED_SETTINGS.update( pickle.load( open('cam_data.bin', 'rb')) )

def save_data(s):
    pickle.dump(s, open('cam_data.bin', 'wb'))

def plot(xyz):
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D

    fig = plt.figure()
    ax = fig.gca(projection = '3d')
    ax.scatter(x, y, z)
    while True:
        plt.show()
        key = cv2.waitKey(100)
        if key & 0xFF == 'q':
            break

def _view_matrix(m):
    m = eval(repr(m)[5:])
    return str(m)

def lasers_calibration(calibration_data, images):
    margin = int(len(images)/3)

    def compute_pc(X):
        # Load point cloud

        n = X.shape[0]
        Xm = X.sum(axis=0) / n
        M = np.array(X - Xm).T

        # Equivalent to:
        #  numpy.linalg.svd(M)[0][:,2]
        # But 1200x times faster for large point clouds
        U = linalg.svds(M, k=2)[0]
        normal = np.cross(U.T[0], U.T[1])
        if normal[2] < 0:
            normal *= -1

        dist = np.dot(normal, Xm)
        std = np.dot(M.T, normal).std()
        return (dist, normal, std)

    images = images[margin:-margin]
    for laser in range(2):
        ranges = [ int(fn.rsplit('/')[-1].split('_')[1].split('.')[0]) for fn in  images]
        im = [METADATA[x] for x in images]

        assert len(ranges) == len(im)

        obj = cloudify(calibration_data, './capture', [laser], ranges, pure_images=True, method='simpleline', camera=im)
        dist, normal, std = compute_pc(obj._mesh.vertexes)

        print("laser %d:"%laser)
        print("Normal vector    %s"%(_view_matrix(normal)))
        print("Plane distance    %.4f mm"%(dist))
#        print("Standard deviation    {0} mm".format(std))

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
        objp = np.zeros((np.multiply(*PATTERN_MATRIX_SIZE), 3), np.float32)
        objp[:, :2] = np.mgrid[0:PATTERN_MATRIX_SIZE[0], 0:PATTERN_MATRIX_SIZE[1]].T.reshape(-1, 2)
        objp = np.multiply(objp, PATTERN_SQUARE_SIZE)
        if objp.size:
            try:
                ret, rvecs, tvecs = cv2.solvePnP(objp, corners, calibration_data.camera_matrix, calibration_data.distortion_vector)
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

#        x = np.array(x)
#        y = np.array(y)
#        z = np.array(z)
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
                print("ISNOGOOD !! %s !~= %s"%(t, ESTIMATED_PLATFORM_TRANSLAT))

            COLLECTED_SETTINGS['translation_vector'] = t
            COLLECTED_SETTINGS['rotation_matrix'] = R

            calibration_data.platform_rotation = R
            calibration_data.platform_translation = t

            save_data(COLLECTED_SETTINGS)

    print("")
    return buggy_captures

def webcam_calibration(calibration_data, images):
    obj_points = []
    img_points = []
    found_nr = 0

    pattern_points = np.zeros((np.prod(PATTERN_MATRIX_SIZE), 3), np.float32)
    pattern_points[:, :2] = np.indices(PATTERN_MATRIX_SIZE).T.reshape(-1, 2)
#    pattern_points *= (PATTERN_SQUARE_SIZE)

    failed_serie = 0
    term = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, 30, 0.1)

    for idx, fn in enumerate(images):
        gui.progress('Webcam calibration %s (%d found)... ' % (fn, found_nr), idx, len(images))
        img = cv2.imread(fn, 0)
        # rotation:
        img = cv2.transpose(img)
        img = cv2.flip(img, 1)

        if img is None:
            print("Failed to load", fn)
            continue

        w, h = img.shape[:2]

        found, corners = cv2.findChessboardCorners(img, PATTERN_MATRIX_SIZE, flags=cv2.CALIB_CB_FAST_CHECK+cv2.CALIB_CB_NORMALIZE_IMAGE)

        if not found:
            if found_nr > 20 and failed_serie > 10:
                break
            failed_serie += 1
            continue

        failed_serie = 0
        found_nr += 1
        cv2.cornerSubPix(img, corners, (11, 11), (-1, -1), term)

        # save data
        METADATA[fn]['chess_corners'] = corners
        img_points.append(corners.reshape(-1, 2))
        obj_points.append(pattern_points)

        # display
        vis = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        cv2.drawChessboardCorners(vis, PATTERN_MATRIX_SIZE, corners, found)
        gui.display(vis[int(vis.shape[0]/3):-100,], 'chess')

    print("\nComputing calibration...")
    if SKIP_CAM_CALIBRATION:
        calibration_data.camera_matrix = np.array( [[1432.67615, 0.0, 487.896461], [0.0, 1426.651, 645.154025], [0.0, 0.0, 1.0]])
        calibration_data.distortion_vector = np.array([[-0.02902898, 0.16920005, -0.00041681, -0.00092935, 0.3478203]])
        return

    rms, camera_matrix, dist_coefs, rvecs, tvecs = cv2.calibrateCamera(obj_points, img_points, (w, h), None, None)
    camera_matrix, roi = cv2.getOptimalNewCameraMatrix(camera_matrix, dist_coefs, (w, h), 1, (w, h))

    COLLECTED_SETTINGS['camera_matrix'] = camera_matrix
    COLLECTED_SETTINGS['distortion_vector'] = dist_coefs.ravel()
    COLLECTED_SETTINGS['roi'] = roi

    calibration_data.camera_matrix = camera_matrix
    calibration_data.distortion_vector = dist_coefs

    print("camera matrix:\n%s"% _view_matrix(camera_matrix))
    print("distortion coefficients: %s"% _view_matrix(dist_coefs))
    print("ROI: %s"%(repr(roi)))

    save_data(COLLECTED_SETTINGS)


def calibrate():

    path = os.path.expanduser('~/.horus/calibration.json')
    settings = json.load(open(path))['calibration_settings']
    calibration_data = CalibrationData()

    calibration_data.laser_planes[0].distance = settings['distance_left']['value']
    calibration_data.laser_planes[0].normal = settings['normal_left']['value']
    calibration_data.laser_planes[1].distance = settings['distance_right']['value']
    calibration_data.laser_planes[1].normal = settings['normal_right']['value']

    calibration_data.platform_rotation = settings['rotation_matrix']['value']
    calibration_data.platform_translation = settings['translation_vector']['value']

    calibration_data.camera_matrix = settings['camera_matrix']['value']
    calibration_data.distorsion_vector = settings['distortion_vector']['value']

    if os.path.exists('cam_data.bin'):
        o =  pickle.load( open('cam_data.bin', 'rb'))
        calibration_data.platform_translation = o['translation_vector']
        calibration_data.platform_rotation = o['rotation_matrix']
        calibration_data.distortion_vector = o['distortion_vector']
        calibration_data.camera_matrix = o['camera_matrix']

    img_mask = './capture/color_*.png'
    img_names = sorted(glob(img_mask))

    # Now final step: lasers

    webcam_calibration(calibration_data, img_names)
    buggy_captures = platform_calibration(calibration_data)

    good_images = set(METADATA)
    good_images.difference_update(buggy_captures)
    good_images = list(good_images)
    good_images.sort()
    import pickle
    pickle.dump(dict(
            images = good_images,
            metadata = dict(METADATA),
            settings = COLLECTED_SETTINGS
            )
            , open('images.js', 'wb'))

    lasers_calibration(calibration_data, good_images)
    METADATA.clear()
    gui.clear()

