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
from time import sleep

from thotus import model
from thotus.ui import gui
from thotus.linedetect import LineMaker
from thotus.scanner import Scanner, get_board, get_controllers
from thotus.projection import CalibrationData, PointCloudGeneration, clean_model, fit_plane, fit_circle
from thotus.calibration import calibrate
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
    get_scanner() # sync scanner startup
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
    D = 0.15

    for n in range(360):
        if definition > 1 and n%definition != 0:
            continue
        gui.progress("scan", n, 360)
        b.motor_move(1*definition)
        sleep(0.2)
        if kind & COLOR:
            disp( b.save('color_%03d.png'%n) , '')
        if kind & LASER1:
            b.laser_on(0)
#            b.wait_capture(2+SLOWDOWN)
            sleep(D)
            disp( b.save('laser0_%03d.png'%n), 'LEFT')
            b.laser_off(0)
        if kind & LASER2:
            b.laser_on(1)
#            b.wait_capture(2+SLOWDOWN)
            sleep(D)
            disp( b.save('laser1_%03d.png'%n) , 'RIGHT')
            b.laser_off(1)
    gui.clear()

def recognize_pure():
    return recognize(pure_images=True)

def recognize(pure_images=False, rotated=False):
    path = os.path.expanduser('~/.horus/calibration.json')
    settings = json.load(open(path))['calibration_settings']
    calibration_data = CalibrationData()

    calibration_data.distortion_vector = np.array(settings['distortion_vector']['value'])
    calibration_data.camera_matrix = np.array( settings['camera_matrix']['value'] )

    calibration_data.laser_planes[0].distance = settings['distance_left']['value']
    calibration_data.laser_planes[0].normal = settings['normal_left']['value']
    calibration_data.laser_planes[1].distance = settings['distance_right']['value']
    calibration_data.laser_planes[1].normal = settings['normal_right']['value']

    calibration_data.platform_rotation = settings['rotation_matrix']['value']
    calibration_data.platform_translation = settings['translation_vector']['value']

    calibration_data._roi = (9, 8, 1262, 942) # hardcoded ROI

    # Pointcloudize !!
    obj = model.Model(None, is_point_cloud=True)
    obj._add_mesh()
    obj._mesh._prepare_vertex_count(4000000)

    color = (255, 0, 0)

    def append_point(point, radius=0.1, height=15):
        point = point / 1000.0
        rho = np.abs(np.sqrt(np.square(point[0, :]) + np.square(point[1, :])))
        z = point[2, :]

        idx = np.where((z >= 0) &
                       (z <= height) &
                       (rho < radius))[0]

        for i in idx:
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
            i2 = calibration_data.undistort_image(cv2.imread(WORKDIR+'/color_%03d.png'%n))
        for laser in range(2):
            i1 = calibration_data.undistort_image(cv2.imread(WORKDIR+'/laser%d_%03d.png'%(laser, n)))
            if pure_images:
                diff = i1
            else:
                diff = cv2.absdiff(i1, i2)

            if not rotated:
                diff = np.rot90(diff, 3)


            processed = lm.from_lineimage(diff[:,:,0], laser) # good for lines
#            processed = lm.from_image(diff[:,:,0])
#            processed = lm.from_pureimage(diff[:,:,0]) # good for model

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
            diff = diff * 10

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
    save_scene("capture.ply", obj)
    gui.clear()

