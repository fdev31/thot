import cv2
import numpy as np

from thotus import settings

def denoise(img, power=5):
    k = np.ones((power, power), np.uint8)
    return cv2.dilate(cv2.erode(img, k), k).astype(np.uint8)

def compute_noise_mask(img, power=5, threshold=4):
    img = np.clip((img*1.0-threshold), 0, 255) # convert to float & clamp
    return denoise(img, power)

def subtract(img1, img2, blur=None, mask=None):
    if img2 is not None:
        img = cv2.subtract(img1, img2)
    else:
        img = img1
    if blur:
        img = cv2.blur(img, blur)
    if mask is not None:
        img = mask_contours(img, mask)
    return img

def mask_contours(image, contours=None, mask=None):
    if contours is not None:
        mask = np.zeros(image.shape, np.uint8)
        cv2.fillConvexPoly(mask, contours, 255)
    return cv2.bitwise_and(image, image, mask=mask)

def imread(path, format="rgb", calibrated=False):
    i = cv2.imread(path)
    if i is None:
        if format == "full":
            return None, None
        return
    if settings.ROTATE:
        i = cv2.flip(cv2.transpose(i), 1)

    if format == 'grey':
        return cv2.cvtColor(i, cv2.COLOR_RGB2HSV)[:,:,2]
    elif format == 'hsv':
        return cv2.cvtColor(i, cv2.COLOR_RGB2HSV)
    elif format == "full":
        return i, cv2.cvtColor(i, cv2.COLOR_RGB2HSV)
    return i
