SKIP = 0
from thotus.ui import gui
from thotus.projection import CalibrationData, PointCloudGeneration, clean_model, fit_plane, fit_circle

import pickle


def calibrate():
    COLLECTED_SETTINGS = {}

    def save_data(s):
        pickle.dump(s, open('cam_data.bin', 'wb'))
    import os
    import json
    import numpy as np
    path = os.path.expanduser('~/.horus/calibration.json')
    settings = json.load(open(path))['calibration_settings']
    calibration_data = CalibrationData()


    calibration_data.laser_planes[0].distance = settings['distance_left']['value']
    calibration_data.laser_planes[0].normal = settings['normal_left']['value']
    calibration_data.laser_planes[1].distance = settings['distance_right']['value']
    calibration_data.laser_planes[1].normal = settings['normal_right']['value']

    calibration_data.platform_rotation = settings['rotation_matrix']['value']
    calibration_data.platform_translation = settings['translation_vector']['value']


    import numpy as np
    import cv2

    # local modules
    def splitfn(p):
        p, e = p.rsplit('.', 1)
        p, d = p.rsplit('/', 1)
        return p, d, e

    # built-in modules
    import os

    import sys
    import getopt
    from glob import glob

    args, img_mask = getopt.getopt(sys.argv[1:], '', ['debug=', 'square_size='])
    args = dict(args)
    args.setdefault('--debug', './output/')
    args.setdefault('--square_size', 1.0)
    if not img_mask:
        img_mask = './calibration_target/color_0*.png'
    else:
        img_mask = img_mask[0]

    img_names = glob(img_mask)
    debug_dir = args.get('--debug')
    if not os.path.isdir(debug_dir):
        os.mkdir(debug_dir)
    square_size = float(args.get('--square_size'))

    pattern_size = (11, 6)
    pattern_square_size = 13.0
    origin_distance = 38.0 # camera to disc origin distance ?
    estimated_t = [-5, 90, 320] # reference 
    pattern_points = np.zeros((np.prod(pattern_size), 3), np.float32)
    pattern_points[:, :2] = np.indices(pattern_size).T.reshape(-1, 2)
    pattern_points *= square_size

    obj_points = []
    img_points = []
    h, w = 0, 0
    from collections import defaultdict
    image_metadata = defaultdict(lambda: {})
    # basic + webcam calibration data
    for fn in img_names:
        print('processing %s... ' % fn, end='')
        img = cv2.imread(fn, 0)
        # rotation:
        img = cv2.transpose(img)
        img = cv2.flip(img, 1)

        if img is None:
            print("Failed to load", fn)
            continue

        w, h = img.shape[:2]
        found, corners = cv2.findChessboardCorners(img, pattern_size, flags=cv2.CALIB_CB_FAST_CHECK )
        print(found)
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
            print('chessboard not found')
            continue

        img_points.append(corners.reshape(-1, 2))
        obj_points.append(pattern_points)

        print('ok')

    # calculate camera distortion
    if SKIP < 2:
        print("computing calibration...")
        # NOT GOOD :((((
        rms, camera_matrix, dist_coefs, rvecs, tvecs = cv2.calibrateCamera(obj_points, img_points, (w, h), None, None)
        print("\nRMS:", rms)
        camera_matrix, roi = cv2.getOptimalNewCameraMatrix(camera_matrix, dist_coefs, (w, h), 1, (w, h))
        COLLECTED_SETTINGS['camera_matrix'] = camera_matrix
        COLLECTED_SETTINGS['distortion_vector'] = dist_coefs.ravel()
        COLLECTED_SETTINGS['roi'] = roi
        save_data(COLLECTED_SETTINGS)
    else:
        COLLECTED_SETTINGS = pickle.load( open('cam_data.bin', 'rb'))
        camera_matrix = COLLECTED_SETTINGS['camera_matrix']
        dist_coefs = COLLECTED_SETTINGS['distortion_vector']
        roi = COLLECTED_SETTINGS['roi']

    print("camera matrix:\n", camera_matrix)
    print("distortion coefficients: ", dist_coefs)
    print("ROI: ", roi)

    # now platform calibration

    x = []
    y = []
    z = []

    calibration_data.camera_matrix = camera_matrix
    calibration_data.distortion_vector = dist_coefs

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
                print("Error solving %s : %s"%(fn, e))
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
    points = np.array(list(zip(y, x, z)))

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
            print(" Translation: " + str(t))
            print(" Rotation: " + str(R).replace('\n', ''))
            print(" Normal: " + str(normal))
            if np.linalg.norm(t - estimated_t) > 100:
                print("PAS BON !! %s !~= %s"%(t, estimated_t))

            COLLECTED_SETTINGS['translation_vector'] = t
            COLLECTED_SETTINGS['rotation_matrix'] = R

            save_data(COLLECTED_SETTINGS)

    # Now final step: lasers
    return 3
