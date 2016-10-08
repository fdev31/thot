from __future__ import print_function

import os
import json
from collections import defaultdict

try:
    import pudb
except ImportError:
    pass
import cv2
import numpy as np

from thotus import model
from thotus.ui import gui
from thotus.linedetect import LineMaker
from thotus.scanner import Scanner
from thotus.projection import CalibrationData, PointCloudGeneration, clean_model
from thotus.ply import save_scene

SLOWDOWN=0

WORKDIR="./capture"

try:
    os.mkdir(WORKDIR)
except:
    pass

def capture():
    s = Scanner(out=WORKDIR)
    for n in range(3):
        print("%d..."%(n+1))
    try:
        _scan(s)
    except KeyboardInterrupt:
        s.close()
        print("bye bye")

def _scan(b, definition=1):
    def disp(img, text):
        gui.display(np.rot90(img, 3), text='scan', resize=(640,480))

    for n in range(360):
        if definition > 1 and n%definition != 0:
            continue
        b.wait_capture()
        disp( b.save('color_%03d.png'%n) , '')
        b.laser_on(0)
        b.wait_capture(2+SLOWDOWN)
        disp( b.save('laser0_%03d.png'%n), 'LEFT')
        b.laser_off(0)
        b.laser_on(1)
        b.wait_capture(2+SLOWDOWN)
        disp( b.save('laser1_%03d.png'%n) , 'RIGHT')
        b.laser_off(1)
        b.motor_move(1*definition)
        gui.progress("scan", n, 360)

def recognise():
    path = os.path.expanduser('~/.horus/calibration.json')
    settings = json.load(open(path))['calibration_settings']
    calibration_data = CalibrationData()
    calibration_data.camera_matrix = np.array( settings['camera_matrix']['value'] )
    calibration_data.distortion_vector = np.array(settings['distortion_vector']['value'])
    calibration_data.laser_planes[0].distance = settings['distance_left']['value']
    calibration_data.laser_planes[0].normal = settings['normal_left']['value']
    calibration_data.laser_planes[1].distance = settings['distance_right']['value']
    calibration_data.laser_planes[1].normal = settings['normal_right']['value']
    calibration_data.platform_rotation = settings['rotation_matrix']['value']
    calibration_data.platform_translation = settings['translation_vector']['value']

    # Pointcloudize !!
    obj = model.Model(None, is_point_cloud=True)
    obj._add_mesh()
    obj._mesh._prepare_vertex_count(4000000)

    color = (255, 0, 0)

    def append_point(point):
        for i in range(point.shape[1]):
            obj._mesh._add_vertex(
                point[0][i], point[1][i], point[2][i],
                color[0], color[1], color[2])
        # Compute Z center
        if point.shape[1] > 0:
            zmax = max(point[2])
            if zmax > obj._size[2]:
                obj._size[2] = zmax

    lm = LineMaker()
    pcg = PointCloudGeneration(calibration_data)

    sliced_lines = defaultdict(lambda: [None, None])

    for n in range(360):
        i2 = cv2.imread(WORKDIR+'/color_%03d.png'%n)
        for laser in range(2):
            i1 = cv2.imread(WORKDIR+'/laser%d_%03d.png'%(laser, n))

            diff = np.rot90(cv2.absdiff(i1, i2), 3)

            processed = lm.from_image(diff[:,:,0])

            gui.progress("analyse", n, 360)

            # project 3D point

            if lm.points:
                sliced_lines[n][laser] = (
                    np.deg2rad(n),
                    lm.points,
                    laser
                )

            # now transform for display

            diff[:,:,1] = processed

            img = diff[400:-100,:].copy()

            gui.display(img,"lines")


    for angle, lasers in sliced_lines.items():
        pc = pcg.compute_point_cloud(*lasers[0])
        if pc is not None:
            append_point(pc)
        pc = pcg.compute_point_cloud(*lasers[1])
        if pc is not None:
            append_point(pc)

    # post-process the mesh
    obj = clean_model(obj)
    save_scene(WORKDIR+".ply", obj)

