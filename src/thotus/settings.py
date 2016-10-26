import os
import json
import pickle
import numpy as np

(
('platform_rotation', 'rotation_matrix'),
('platform_translation', 'translation_vector'),
('camera_matrix', 'camera_matrix'),
('distortion_vector', 'distortion_vector'),
)

configuration = 'thot'
single_laser = None


WORKDIR="./capture"

try:
    os.mkdir(WORKDIR)
except:
    pass


def _cast(val):
    if isinstance(val, (list, tuple)):
        val = np.array(val)
    return val

def load_data(calibration_data):
    if configuration[0] == 'h':
        h = _from_horus()
        for n in ('platform_rotation', 'platform_translation', 'camera_matrix', 'distortion_vector', 'laser_planes'):
            setattr(calibration_data, n, _cast(h[n]))
    else:
        o =  pickle.load( open('cam_data.bin', 'rb'))
        for n in ('platform_rotation', 'platform_translation', 'camera_matrix', 'distortion_vector', 'laser_planes'):
            setattr(calibration_data, n, _cast(o[n]))
    return calibration_data

def save_data(s):
    pickle.dump({
        'distortion_vector': s._distortion_vector,
        'camera_matrix': s._camera_matrix,

        'platform_translation': s.platform_translation,
        'platform_rotation': s.platform_rotation,

        'laser_planes': s.laser_planes,
        }, open('cam_data.bin', 'wb'))


def _from_horus():
    path = os.path.expanduser('~/.horus/calibration.json')
    s = json.load(open(path))['calibration_settings']
    return {
        'distortion_vector': _cast(s['distortion_vector']['value']),
        'camera_matrix': _cast(s['camera_matrix']['value']),

        'platform_translation': _cast(s['translation_vector']['value']),
        'platform_rotation': _cast(s['rotation_matrix']['value']),

        'laser_planes': [
            LaserPlane(_cast(s['normal_left']['value']), s['distance_left']['value']),
            LaserPlane(_cast(s['normal_right']['value']), s['distance_right']['value']),
            ]
        }

def compare():
    path = os.path.expanduser('~/.horus/calibration.json')
    settings = _from_horus()
    o =  pickle.load( open('cam_data.bin', 'rb'))
    SEP="\nvs\n"
    print("HORUS"+SEP+"THOT")
    for n in ('platform_rotation', 'platform_translation', 'camera_matrix', 'distortion_vector', 'laser_planes'):
        print(("\n   %s   "%(n).capitalize()).center(80, '#' ))
        print("%s%s%s"%(settings[n] , SEP , o[n]))

class LaserPlane(object):
    def __init__(self, n=None, d=None):
        self.normal = n
        self.distance = d

    def __repr__(self):
        return ("<Plane %s @ %s>"%(self.normal, self.distance))
