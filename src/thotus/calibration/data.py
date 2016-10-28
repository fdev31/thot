try:
    import md5
    md5 = md5.new
except ImportError:
    from hashlib import md5

from thotus import settings

import cv2

class CalibrationData(object):

    def __init__(self):
        self.width = 0
        self.height = 0

        self._camera_matrix = None
        self._distortion_vector = None
        self._roi = None
        self._dist_camera_matrix = None
        self._weight_matrix = None

        self._md5_hash = None

        self.laser_planes = [settings.Attribute() for _ in settings.get_laser_range()]
        self.platform_rotation = None
        self.platform_translation = None

    def __setitem__(self, name, val):
        return setattr(self, name, val)

    def __getitem__(self, name):
        try:
            return getattr(self, name)
        except AttributeError as e:
            raise KeyError(*e.args)

    def undistort_image(self, image):
        cam_matrix , roi = cv2.getOptimalNewCameraMatrix(self.camera_matrix, self.distortion_vector, image.shape[:2], 1, image.shape[:2])
        dst = cv2.undistort(image,
                self.camera_matrix,
                self.distortion_vector,
                None,
                cam_matrix)
        x, y, w, h = roi
        dst = dst[x:x+w,y:y+h]
        return dst

    @property
    def camera_matrix(self):
        return self._camera_matrix

    @camera_matrix.setter
    def camera_matrix(self, value):
        self._camera_matrix = value

    @property
    def distortion_vector(self):
        return self._distortion_vector

    @distortion_vector.setter
    def distortion_vector(self, value):
        self._distortion_vector = value
