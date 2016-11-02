# -*- coding: utf-8 -*-
# This file is part of the Horus Project

__author__ = 'Jesús Arroyo Torrens <jesus.arroyo@bq.com>'
__copyright__ = 'Copyright (C) 2014-2016 Mundo Reader S.L.\
                 Copyright (C) 2013 David Braam from Cura Project'
__license__ = 'GNU General Public License v2 http://www.gnu.org/licenses/gpl2.html'

import os

import numpy as np
np.seterr(all='ignore')


class Model(object):
    """
    Each object has a Mesh and a 3x3 transformation matrix to rotate/scale the object.
    """

    def __init__(self, origin_filename, is_point_cloud=False):
        self._origin_filename = origin_filename
        self._is_point_cloud = is_point_cloud

        if origin_filename is None:
            self._name = 'None'
        else:
            self._name = os.path.basename(origin_filename)
        if '.' in self._name:
            self._name = os.path.splitext(self._name)[0]
        self._mesh = None
        self._size = np.array([0.0, 0.0, 0.0])

    def _add_mesh(self):
        self._mesh = BaseMesh(self)
        return self._mesh


class BaseMesh(object):
    """
    A mesh is a list of 3D triangles build from vertexes.
    Each triangle has 3 vertexes. It can be also a point cloud.
    A "VBO" can be associated with this object, which is used for rendering this object.
    """

    def __init__(self, obj):
        self.vertexes = None
        self.colors = None
        self.normal = None
        self.vertex_count = 0
        self.vbo = None
        self._obj = obj

    def _add_vertex(self, x, y, z, r=255, g=255, b=255):
        n = self.vertex_count
        self.vertexes[n], self.colors[n] = (x, y, z), (r, g, b)
        self.vertex_count += 1

    def _prepare_vertex_count(self, vertex_number):
        # Set the amount of vertex before loading data in them. This way we can
        # create the np arrays before we fill them.
        self.vertexes = np.zeros((vertex_number, 3), np.float32)
        self.colors = np.zeros((vertex_number, 3), np.int32)
        self.normal = np.zeros((vertex_number, 3), np.float32)
        self.vertex_count = 0

    def _calculate_normals(self):
        # Calculate the normals
        tris = self.vertexes.reshape(self.vertex_count / 3, 3, 3)
        normals = np.cross(tris[::, 1] - tris[::, 0], tris[::, 2] - tris[::, 0])
        normals /= np.linalg.norm(normals)
        n = np.concatenate((np.concatenate((normals, normals), axis=1), normals), axis=1)
        self.normal = n.reshape(self.vertex_count, 3)
