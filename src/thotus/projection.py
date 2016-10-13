# -*- coding: utf-8 -*-
# This file is part of the Horus Project

__author__ = 'Jesús Arroyo Torrens <jesus.arroyo@bq.com>'
__copyright__ = 'Copyright (C) 2014-2016 Mundo Reader S.L.'
__license__ = 'GNU General Public License v2 http://www.gnu.org/licenses/gpl2.html'


try:
    import md5
    md5 = md5.new
except ImportError:
    from hashlib import md5

import cv2
import numpy as np
from scipy import optimize

from thotus.model import Model

def clean_model(obj, delta=0.5, threshold=10):
    # delta is max distance
    return obj # remove lost vertex (no friends, less than threshold)

def residuals_circle(parameters, points, s, r, point):
    r_, s_, Ri = parameters
    plane_point = s_ * s + r_ * r + np.array(point)
    distance = [np.linalg.norm(plane_point - np.array([x, y, z])) for x, y, z in points]
    res = [(Ri - dist) for dist in distance]
    return res

def distance2plane(p0, n0, p):
    return np.dot(np.array(n0), np.array(p) - np.array(p0))

def residuals_plane(parameters, data_point):
    px, py, pz, theta, phi = parameters
    nx, ny, nz = np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)
    distances = [distance2plane(
        [px, py, pz], [nx, ny, nz], [x, y, z]) for x, y, z in data_point]
    return distances

def fit_plane(data):
    estimate = [0, 0, 0, 0, 0]  # px,py,pz and zeta, phi
    # you may automize this by using the center of mass data
    # note that the normal vector is given in polar coordinates
    best_fit_values, ier = optimize.leastsq(residuals_plane, estimate, args=(data))
    xF, yF, zF, tF, pF = best_fit_values

    # point  = [xF,yF,zF]
    point = data[0]
    normal = -np.array([np.sin(tF) * np.cos(pF), np.sin(tF) * np.sin(pF), np.cos(tF)])

    return point, normal

def fit_circle(point, normal, points):
    # creating two inplane vectors
    # assuming that normal not parallel x!
    s = np.cross(np.array([1, 0, 0]), np.array(normal))
    s = s / np.linalg.norm(s)
    r = np.cross(np.array(normal), s)
    r = r / np.linalg.norm(r)  # should be normalized already, but anyhow

    # Define rotation
    R = np.array([s, r, normal]).T

    estimate_circle = [0, 0, 0]  # px,py,pz and zeta, phi
    best_circle_fit_values, ier = optimize.leastsq(
        residuals_circle, estimate_circle, args=(points, s, r, point))

    rF, sF, RiF = best_circle_fit_values

    # Synthetic Data
    center_point = sF * s + rF * r + np.array(point)
    synthetic = [list(center_point + RiF * np.cos(phi) * r + RiF * np.sin(phi) * s)
                 for phi in np.linspace(0, 2 * np.pi, 50)]
    [cxTupel, cyTupel, czTupel] = [x for x in zip(*synthetic)]

    return center_point, R, [cxTupel, cyTupel, czTupel]

class PointCloudGeneration(object):

    def __init__(self, calibration_data):
        self.calibration_data = calibration_data

    def compute_point_cloud(self, theta, points_2d, index):
        # Load calibration values
        R = np.matrix(self.calibration_data.platform_rotation)
        t = np.matrix(self.calibration_data.platform_translation).T
        # Compute platform transformation
        Xwo = self.compute_platform_point_cloud(points_2d, R, t, index)
        # Rotate to world coordinates
        c, s = np.cos(-theta), np.sin(-theta)
        Rz = np.matrix([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        Xw = Rz * Xwo
        # Return point cloud
        if Xw.size > 0:
            return np.array(Xw)
        else:
            return None

    def compute_platform_point_cloud(self, points_2d, R, t, index):
        # Load calibration values
        n = self.calibration_data.laser_planes[index].normal
        d = self.calibration_data.laser_planes[index].distance
        # Camera system
        Xc = self.compute_camera_point_cloud(points_2d, d, n)
        # Compute platform transformation
        return R.T * Xc - R.T * t

    def compute_camera_point_cloud(self, points_2d, d, n):
        # Load calibration values
        fx = self.calibration_data.camera_matrix[0][0]
        fy = self.calibration_data.camera_matrix[1][1]
        cx = self.calibration_data.camera_matrix[0][2]
        cy = self.calibration_data.camera_matrix[1][2]
        # Compute projection point
        u, v = points_2d
        x = np.concatenate(((u - cx) / fx, (v - cy) / fy, np.ones(len(u)))).reshape(3, len(u))
        # Compute laser intersection
        return d / np.dot(n, x) * x

class LaserPlane(object):
    def __init__(self):
        self.normal = None
        self.distance = None

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

        self.laser_planes = [LaserPlane(), LaserPlane()]
        self.platform_rotation = None
        self.platform_translation = None

    def set_resolution(self, width, height):
        if self.width != width or self.height != height:
            self.width = width
            self.height = height
            self._compute_weight_matrix()

    def undistort_image(self, image):
        x, roi = cv2.getOptimalNewCameraMatrix(self.camera_matrix, self.distortion_vector, image.shape[:2], 1, image.shape[:2])
        dst = cv2.undistort(image,
                self.camera_matrix,
                self.distortion_vector,
                None,
                x)
        x, y, w, h = roi
#        dst = dst[x:x+w,y:y+h]
        return dst


    @property
    def camera_matrix(self):
        return self._camera_matrix

    @camera_matrix.setter
    def camera_matrix(self, value):
        self._camera_matrix = value
        self._compute_dist_camera_matrix()

    @property
    def distortion_vector(self):
        return self._distortion_vector

    @distortion_vector.setter
    def distortion_vector(self, value):
        self._distortion_vector = value
        self._compute_dist_camera_matrix()

    @property
    def dist_camera_matrix(self):
        return self._dist_camera_matrix

    @property
    def weight_matrix(self):
        return self._weight_matrix

    def _compute_dist_camera_matrix(self):
        if self._camera_matrix is not None and self._distortion_vector is not None:
            self._dist_camera_matrix, self._roi = cv2.getOptimalNewCameraMatrix(
                self._camera_matrix, self._distortion_vector,
                (int(self.width), int(self.height)), alpha=1)
            self._md5_hash = md5()
            self._md5_hash.update(self._camera_matrix)
            self._md5_hash.update(self._distortion_vector)
            self._md5_hash = self._md5_hash.hexdigest()

    def _compute_weight_matrix(self):
        self._weight_matrix = np.array((np.matrix(np.linspace(0, self.width - 1, self.width)).T *
                                        np.matrix(np.ones(self.height))).T)

    def check_calibration(self):
        if self.camera_matrix is None or self.distortion_vector is None:
            return False
        for plane in self.laser_planes:
            if plane.distance is None or plane.normal is None:
                return False
            if plane.distance == 0.0 or self._is_zero(plane.normal):
                return False
        if self.platform_rotation is None or self.platform_translation is None:
            return False
        if self._is_zero(self.platform_rotation) or self._is_zero(self.platform_translation):
            return False
        return True

    def _is_zero(self, array):
        return np.all(array == 0.0)

    def md5_hash(self):
        return self._md5_hash
