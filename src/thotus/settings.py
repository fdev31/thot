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
skip_calibration = True

LASER_COUNT = 2

PATTERN_MATRIX_SIZE = (11, 6)
PATTERN_SQUARE_SIZE = 13.0
PATTERN_ORIGIN = 38.8 # distance plateau to second row of pattern

def get_pattern_points():
    pattern_points = np.zeros((np.prod(PATTERN_MATRIX_SIZE), 3), np.float32)
    pattern_points[:, :2] = np.indices(PATTERN_MATRIX_SIZE).T.reshape(-1, 2)
    return np.multiply(pattern_points, PATTERN_SQUARE_SIZE)

WORKDIR="./capture"
CALIBDIR="./calibration"
FILEFORMAT='jpg' # or png

class Attribute(dict):

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError("name")

    def __repr__(self):
        s = []
        it = list(self.items()) + list(self.__dict__.items())
        it.sort()
        for v in it:
            s.append("%s=%s"%v)
        return "<%s>"%(', '.join(s))

try:
    os.mkdir(WORKDIR)
except:
    pass

try:
    os.mkdir(CALIBDIR)
except:
    pass

def _cast(val):
    if isinstance(val, (list, tuple)):
        val = np.array(val)
    return val

def get_laser_range():
    if single_laser is None:
        return range(LASER_COUNT)
    else:
        return [single_laser]

def load_data(calibration_data):
    src = _from_horus() if configuration[0] == 'h' else  pickle.load( open('cam_data.bin', 'rb'))
    for n in ('platform_rotation', 'platform_translation', 'camera_matrix', 'distortion_vector', 'laser_planes'):
        setattr(calibration_data, n, _cast(src[n]))
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

        'laser_planes': np.array([
            Attribute(normal=_cast(s['normal_left']['value']), distance=s['distance_left']['value']),
            Attribute(normal=_cast(s['normal_right']['value']),distance=s['distance_right']['value']),
            ])
        }

def _view_matrix(m):
    try:
        m = repr(m)[5:]
        m = m[1:1+m.rindex(']')]
    except Exception:
        return str(m)
    else:
        return str(eval(m))

def compare():
    " Display horus & thot configurations side by side "
    path = os.path.expanduser('~/.horus/calibration.json')
    settings = _from_horus()
    o =  pickle.load( open('cam_data.bin', 'rb'))
    SEP="\n"
    print("HORUS"+SEP+"THOT")
    for n in ('platform_rotation', 'platform_translation', 'camera_matrix', 'distortion_vector', 'laser_planes'):
        print(("   %s   "%(n).upper().replace('_', ' ')).center(80, '-' ))
        v1 = settings[n]
        v2 = o[n]
        if n != 'laser_planes':
            v1 = _view_matrix(v1)
            v2 = _view_matrix(v2)
        print("%s%s%s"%(v1 , SEP, v2))
