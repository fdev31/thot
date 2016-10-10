import os
import sys
import json
import pickle
from glob import glob
from collections import defaultdict

SKIP = 3
from thotus.ui import gui
from thotus.projection import CalibrationData, PointCloudGeneration, clean_model, fit_plane, fit_circle
from thotus.linedetect import LineMaker, compute_plane
from thotus.cloudify import cloudify
from thotus.ply import save_scene

import cv2
import numpy as np
from scipy.sparse import linalg

def _view_matrix(m):
    m = eval(repr(m)[5:])
    return str(m)


COLLECTED_SETTINGS = {}
def calibrate():

    def load_data():
        global COLLECTED_SETTINGS
        COLLECTED_SETTINGS.update( pickle.load( open('cam_data.bin', 'rb')) )

    def save_data(s):
        pickle.dump(s, open('cam_data.bin', 'wb'))

    path = os.path.expanduser('~/.horus/calibration.json')
    settings = json.load(open(path))['calibration_settings']
    calibration_data = CalibrationData()


    calibration_data.laser_planes[0].distance = settings['distance_left']['value']
    calibration_data.laser_planes[0].normal = settings['normal_left']['value']
    calibration_data.laser_planes[1].distance = settings['distance_right']['value']
    calibration_data.laser_planes[1].normal = settings['normal_right']['value']

    calibration_data.platform_rotation = settings['rotation_matrix']['value']
    calibration_data.platform_translation = settings['translation_vector']['value']

    img_mask = './capture/color_0*.png'
    img_names = glob(img_mask)
    pattern_size = (11, 6)
    pattern_square_size = 13.0
    origin_distance = 38.88 # distance plateau to second row of pattern
    estimated_t = [-5, 90, 320] # reference 
    pattern_points = np.zeros((np.prod(pattern_size), 3), np.float32)
    pattern_points[:, :2] = np.indices(pattern_size).T.reshape(-1, 2)

    obj_points = []
    img_points = []
    h, w = 0, 0
    image_metadata = defaultdict(lambda: {})
    # basic + webcam calibration data
    for idx, fn in enumerate(img_names):
        gui.progress('processing %s... ' % fn, idx, len(img_names))
        img = cv2.imread(fn, 0)
        # rotation:
        img = cv2.transpose(img)
        img = cv2.flip(img, 1)

        if img is None:
            print("Failed to load", fn)
            continue

        w, h = img.shape[:2]
        found, corners = cv2.findChessboardCorners(img, pattern_size, flags=cv2.CALIB_CB_FAST_CHECK )
        image_metadata[fn]['chess_corners'] = corners
        if SKIP > 1:
            continue
        if found:
            term = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, 30, 0.1)
            cv2.cornerSubPix(img, corners, (5, 5), (-1, -1), term)
            # platform calibration data

        if True:
            vis = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            cv2.drawChessboardCorners(vis, pattern_size, corners, found)
            gui.display(vis, 'chess')

        if not found:
            continue

        img_points.append(corners.reshape(-1, 2))
        obj_points.append(pattern_points)

    # calculate camera distortion
    if SKIP < 2:
        print("\ncomputing calibration...")
        # NOT GOOD :((((
        rms, camera_matrix, dist_coefs, rvecs, tvecs = cv2.calibrateCamera(obj_points, img_points, (w, h), None, None)
        print("\nRMS:", rms)
        camera_matrix, roi = cv2.getOptimalNewCameraMatrix(camera_matrix, dist_coefs, (w, h), 1, (w, h))
        COLLECTED_SETTINGS['camera_matrix'] = camera_matrix
        COLLECTED_SETTINGS['distortion_vector'] = dist_coefs.ravel()
        COLLECTED_SETTINGS['roi'] = roi
        save_data(COLLECTED_SETTINGS)
    else:
        load_data()
        camera_matrix = COLLECTED_SETTINGS['camera_matrix']
        dist_coefs = COLLECTED_SETTINGS['distortion_vector']
        roi = COLLECTED_SETTINGS['roi']

    print("")
    print("camera matrix:\n%s"% _view_matrix(camera_matrix))
    print("distortion coefficients: %s"% _view_matrix(dist_coefs))
    print("ROI: %s"%(repr(roi)))

    # now platform calibration

    x = []
    y = []
    z = []

    calibration_data.camera_matrix = camera_matrix
    calibration_data.distortion_vector = dist_coefs
    buggy_captures = set()

    if SKIP < 3:
        pcg = PointCloudGeneration(calibration_data)
        for fn in image_metadata:
            corners = image_metadata[fn]['chess_corners']
            objp = np.zeros((np.multiply(*pattern_size), 3), np.float32)
            objp[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2)
            objp = np.multiply(objp, pattern_square_size)
            if objp.size:
                try:
                    ret, rvecs, tvecs = cv2.solvePnP(objp, corners, camera_matrix, dist_coefs)
                except Exception as e:
                    buggy_captures.add(fn)
    #                print("Error solving %s : %s"%(fn, e))
                    ret = None
                if ret:
                    pose = (cv2.Rodrigues(rvecs)[0], tvecs, corners)
                    R = pose[0]
                    t = pose[1].T[0]
                    corner = pose[2]
                    normal = R.T[2]
                    distance = np.dot(normal, t)
                    if corners is not None:
                        origin = corners[pattern_size[0] * (pattern_size[1] - 1)][0]
                        origin = np.array([[origin[0]], [origin[1]]])
                        t = pcg.compute_camera_point_cloud(origin, distance, normal)
                        if t is not None:
                            x += [t[0][0]]
                            y += [t[1][0]]
                            z += [t[2][0]]

        x = np.array(x)
        y = np.array(y)
        z = np.array(z)
        print("Points: %d"%x.size)
        points = np.array(list(zip(x, y, z)))

        """
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D

        fig = plt.figure()
        ax = fig.gca(projection = '3d')
        ax.scatter(x, y, z)
        while True:
            plt.show()
            cv2.waitKey(100)
        """

        if points.size > 4:
            # Fitting a plane
            point, normal = fit_plane(points)
            if normal[1] > 0:
                normal = -normal
            # Fitting a circle inside the plane
            center, R, circle = fit_circle(point, normal, points)
            # Get real origin
            t = center - origin_distance * np.array(normal)
            if t is not None:

                print("Platform calibration ")
                print(" Translation: " , _view_matrix(t))
                print(" Rotation: " , _view_matrix(R))
                if np.linalg.norm(t - estimated_t) > 100:
                    print("ISNOGOOD !! %s !~= %s"%(t, estimated_t))

                COLLECTED_SETTINGS['translation_vector'] = t
                COLLECTED_SETTINGS['rotation_matrix'] = R

                save_data(COLLECTED_SETTINGS)
    else:
        load_data()
        t = COLLECTED_SETTINGS['translation_vector']
        R = COLLECTED_SETTINGS['rotation_matrix']

    # Now final step: lasers
    good_images = set(image_metadata)
    good_images.difference_update(buggy_captures)

    ranges = [ int(fn.rsplit('/')[-1].split('_')[1].split('.')[0]) for fn in good_images ]
    ranges.sort()
    margin = 50
    for laser in range(2):
        obj = cloudify(calibration_data, './capture', [laser], ranges[:-margin] if laser == 0 else ranges[margin:], pure_images=True, method='simpleline')
        dist, normal, std = compute_pc(obj._mesh.vertexes)

#        dist, normal, std = compute_plane(obj._mesh.vertexes)
        print("\nNormal vector\n\n%r\n"%(_view_matrix(normal)))
        print("\nPlane distance\n\n%.4f mm\n"%(dist))
        print("\nStandard deviation\n\n{0} mm\n".format(std))

        save_scene("calibration_laser_%d.ply"%laser, obj)

    gui.clear()

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
