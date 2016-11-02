import pickle

from thotus.mesh.ply import save_scene
from thotus.algorithms.projection import PointCloudGeneration
from .model import Model

import numpy as np

def meshify(calibration_data, lines=None, colors=None, camera=False, lasers=range(2), cylinder=(100, 100)):
    pcg = PointCloudGeneration(calibration_data)
    obj = Mesh()
    computer = pcg.compute_camera_point_cloud if camera else pcg.compute_point_cloud
    params = dict(radius=cylinder[1], height=cylinder[0])

    for angle, l in lines.items():
        for laser in lasers:
            x = l[laser]
            if x:
                pc = computer(*x)
                if pc is not None:
                    if colors is not None:
                        params['colors'] = colors[angle][laser]
                    obj.append_point(pc, **params)
    return obj

class Mesh:
    def __init__(self):
        self.obj = Model(None, is_point_cloud=True)
        self.obj._add_mesh()
        self.obj._mesh._prepare_vertex_count(4000000)

    def save(self, filename):
        return save_scene(filename, self.obj)

    @property
    def vertices(self):
        return self.obj._mesh.vertexes[:self.obj._mesh.vertex_count]

    def get(self):
        return self.obj

    def append_point(self, point, radius=100, height=100, colors=None):
        color = (50, 180, 180)  # default color
        obj = self.obj
        rho = np.abs(np.sqrt(np.square(point[0, :]) + np.square(point[1, :])))
        z = point[2, :]

        idx = np.where((z >= 0) &
                       (z <= height) &
                       (rho < radius))[0]

        if colors is not None:
            for i in idx:
                obj._mesh._add_vertex(
                    point[0][i], point[1][i], point[2][i],
                    colors[i][0], colors[i][1], colors[i][2])
        else:
            for i in idx:
                obj._mesh._add_vertex(
                    point[0][i], point[1][i], point[2][i],
                    color[0], color[1], color[2])
        # Compute Z center
        if point.shape[1] > 0:
            zmax = max(point[2])
            if zmax > obj._size[2]:
                obj._size[2] = zmax
