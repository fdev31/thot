from __future__ import print_function

import os
import json
from collections import defaultdict
from threading import Thread

try:
    import pudb
except ImportError:
    pass
import cv2
import numpy as np

from thotus import model
from thotus.ui import gui
from thotus.linedetect import LineMaker
from thotus.scanner import Scanner, get_board, get_controllers
from thotus.projection import CalibrationData, PointCloudGeneration, clean_model
from thotus.ply import save_scene

SLOWDOWN = 1

WORKDIR="./capture"

try:
    os.mkdir(WORKDIR)
except:
    pass

COLOR, LASER1, LASER2 = 1, 2, 4 # bit mask
ALL = COLOR | LASER1 | LASER2

def stop():
    global scanner
    if scanner:
        scanner.close()
    if Viewer.instance:
        Viewer.instance.stop()

scanner = None
def get_scanner():
    global scanner
    if not scanner:
        try:
            scanner = Scanner(out=WORKDIR)
        except RuntimeError as e:
            print("Can't init board: %s"%e.args[0])
    return scanner

lasers = False
def switch_lasers():
    global lasers
    lasers = not lasers
    b = get_board()
    if b:
        if lasers:
            b.lasers_on()
        else:
            b.lasers_off()

class Viewer(Thread):
    instance = None

    def stop(self):
        self.running = False
        self.join()
        self.__class__.instance = None
        gui.clear()

    def run(self):
        s = get_scanner()
        self.running = True
        while self.running:
            s.wait_capture(1)
            gui.display(np.rot90(s.cap.buff, 3), "live", resize=(640,480))

def view():
    if Viewer.instance:
        Viewer.instance.stop()
    else:
        Viewer.instance = Viewer()
        Viewer.instance.start()

def capture_color():
    return capture(COLOR)

def capture_lasers():
    return capture(LASER1|LASER2)

def capture(kind=ALL):
    print("Capture %d"%kind)
    s = get_scanner()
    if not s:
        return
    try:
        _scan(s, kind)
        print("")
    except KeyboardInterrupt:
        print("\naborting...")

def _scan(b, kind=ALL, definition=1):
    print("scan %d / %d"%(kind, ALL))
    def disp(img, text):
        gui.display(np.rot90(img, 3), text=text, resize=(640,480))

    b.lasers_off()

    for n in range(360):
        if definition > 1 and n%definition != 0:
            continue
        gui.progress("scan", n, 360)
        if kind & COLOR:
            b.laser_off(1)
            b.motor_move(1*definition)
            b.wait_capture()
            disp( b.save('color_%03d.png'%n) , '')
        if kind & LASER1:
            b.laser_on(0)
            b.wait_capture(2+SLOWDOWN)
            disp( b.save('laser0_%03d.png'%n), 'LEFT')
        if kind & LASER2:
            b.laser_off(0)
            b.laser_on(1)
            b.wait_capture(2+SLOWDOWN)
            disp( b.save('laser1_%03d.png'%n) , 'RIGHT')
    gui.clear()

def recognize_pure():
    return recognize(pure_images=True)

def recognize(pure_images=False):
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
        if not pure_images:
            i2 = cv2.imread(WORKDIR+'/color_%03d.png'%n)
        for laser in range(2):
            i1 = cv2.imread(WORKDIR+'/laser%d_%03d.png'%(laser, n))
            if pure_images:
                diff = i1
            else:
                diff = np.rot90(cv2.absdiff(i1, i2), 3)

#            processed = lm.from_lineimage(diff[:,:,0], laser)
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

            img = diff[200:-100,:].copy()

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
    gui.clear()

