from collections import defaultdict

from thotus.ui import gui
from thotus import settings
from thotus.image import tools as imtools
from thotus.calibration.chessboard import chess_detect, chess_draw

import cv2
import numpy as np

def calibration(calibration_data, images):
    obj_points = []
    img_points = []
    found_nr = 0

    failed_serie = 0
    term = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.001)
    flags = cv2.CALIB_CB_FAST_CHECK
    pattern_points = settings.get_pattern_points()

    temp_calibration_data = defaultdict(lambda: {})

    for idx, fn in enumerate(images):
        gui.progress('Webcam calibration %s (%d found)... ' % (fn, found_nr), idx, len(images))
        img, hsv = imtools.imread(fn, format="full")
        grey = hsv[:,:,2]

        if img is None:
            print("Failed to load", fn)
            continue

        w, h = img.shape[:2]

        found, corners = chess_detect(grey, flags)

        if not found:
            if found_nr > 20 and failed_serie > 6:
                break
            failed_serie += 1
            continue

        failed_serie = 0
        found_nr += 1
        cv2.cornerSubPix(grey, corners, (11, 11), (-1, -1), term)
        temp_calibration_data[fn]['chess_corners'] = corners
        img_points.append(corners)
        obj_points.append(pattern_points)

        # compute mask coordinates
        p1 = corners[0][0]
        p2 = corners[settings.PATTERN_MATRIX_SIZE[0] - 1][0]
        p3 = corners[settings.PATTERN_MATRIX_SIZE[0] * (settings.PATTERN_MATRIX_SIZE[1] - 1)][0]
        p4 = corners[settings.PATTERN_MATRIX_SIZE[0] * settings.PATTERN_MATRIX_SIZE[1] - 1][0]
        temp_calibration_data[fn]['chess_contour'] = np.array([p1, p2, p4, p3], dtype='int32')

        if idx%settings.ui_base_i == 0:
            chess_draw(img, found, corners)
            gui.display(img, 'chess', resize=True)

    if settings.skip_calibration:
        print("\nskipping camera calibration...")
        try:
            settings.load_data(calibration_data)
        except Exception:
            # Data for Logitech C270
            calibration_data.camera_matrix = np.array(([1430.0, 0.0, 480.0], [0.0, 1430.0, 620.0], [0.0, 0.0, 1.0]))
            calibration_data.distortion_vector = np.array((0.0, 0.0, 0.0, 0.0, 0.0))
        return temp_calibration_data

    print("\nComputing camera calibration...")

    if not obj_points:
        raise ValueError("Unable to detect pattern on screen :(")

    rms, camera_matrix, dist_coefs, rvecs, tvecs = cv2.calibrateCamera(obj_points, img_points, grey.shape, None, None)
    if rms:
        error = 0
        # Compute calibration error
        for i in range(len(obj_points)):
            imgpoints2, _ = cv2.projectPoints(obj_points[i], rvecs[i], tvecs[i], camera_matrix, dist_coefs)
            error += abs(
                    cv2.norm(img_points[i])
                    - cv2.norm(imgpoints2)
                    )
        error /= len(obj_points)
        print("Camera calibration error = %.4fmm"%error)

    calibration_data.camera_matrix = camera_matrix
    calibration_data.distortion_vector = dist_coefs.ravel()

    settings.save_data(calibration_data)
    return temp_calibration_data

