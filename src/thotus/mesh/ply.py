# -*- coding: utf-8 -*-
# This file is part of the Horus Project

__author__ = 'Jesús Arroyo Torrens <jesus.arroyo@bq.com>'
__copyright__ = 'Copyright (C) 2014-2016 Mundo Reader S.L.'
__license__ = 'GNU General Public License v2 http://www.gnu.org/licenses/gpl2.html'

"""
PLY file point cloud loader.

    - Binary, which is easy and quick to read.
    - Ascii, which is harder to read, as can come with windows, mac and unix style newlines.

This module also contains a function to save objects as an PLY file.

http://en.wikipedia.org/wiki/PLY_(file_format)
"""

import struct


def save_scene(filename, _object):
    with open(filename, 'wb') as f:
        save_scene_stream(f, _object)


def save_scene_stream(stream, _object):
    m = _object._mesh

    FACTOR = 10.0

    binary = True

    if m is not None:
        frame = "ply\n"
        if binary:
            frame += "format binary_little_endian 1.0\n"
        else:
            frame += "format ascii 1.0\n"
        frame += "element vertex {0}\n".format(m.vertex_count)
        frame += "property float x\n"
        frame += "property float y\n"
        frame += "property float z\n"
        frame += "property uchar red\n"
        frame += "property uchar green\n"
        frame += "property uchar blue\n"
        frame += "element face 0\n"
        frame += "property list uchar int vertex_indices\n"
        frame += "end_header\n"
        stream.write(frame.encode())
        m.vertexes /= FACTOR
        if m.vertex_count > 0:
            if binary:
                for i in range(m.vertex_count):
                    stream.write(struct.pack("<fffBBB",
                                             m.vertexes[i, 0], m.vertexes[i, 1], m.vertexes[i, 2],
                                             m.colors[i, 0], m.colors[i, 1], m.colors[i, 2]))
            else:
                for i in range(m.vertex_count):
                    stream.write("{0} {1} {2} {3} {4} {5}\n".format(
                                 m.vertexes[i, 0], m.vertexes[i, 1], m.vertexes[i, 2],
                                 m.colors[i, 0], m.colors[i, 1], m.colors[i, 2]))
