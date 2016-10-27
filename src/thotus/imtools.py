import cv2
def imread(path, format="rgb", calibrated=False):
    i = cv2.imread(path)
    if i is None:
        if format == "full":
            return None, None
        return
    i = cv2.flip(cv2.transpose(i), 1)
#    if calibrated:
#        i = calibrated.undistort_image(i)

    if format == 'grey':
        return cv2.cvtColor(i, cv2.COLOR_RGB2HSV)[:,:,2]
    elif format == 'hsv':
        return cv2.cvtColor(i, cv2.COLOR_RGB2HSV)
    elif format == "full":
        return i, cv2.cvtColor(i, cv2.COLOR_RGB2HSV)
    return i
