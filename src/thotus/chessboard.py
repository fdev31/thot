from thotus import settings

import cv2

def chess_detect(img, flags=cv2.CALIB_CB_FAST_CHECK):
    term = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 200, 0.001)
    found, corners = cv2.findChessboardCorners(img, settings.PATTERN_MATRIX_SIZE, flags=flags)
    if found:
        cv2.cornerSubPix(img, corners, (11, 11), (-1, -1), term)
    return found, corners

def chess_draw(img, found, corners, force_color=False):
    for n in range(2):
        try:
            if force_color and n == 0:
                raise TypeError()
            cv2.drawChessboardCorners(img, settings.PATTERN_MATRIX_SIZE, corners, found)
            break
        except TypeError:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return img

