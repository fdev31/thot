import os
import json
import glob
import pickle
import numpy as np

(
('platform_rotation', 'rotation_matrix'),
('platform_translation', 'translation_vector'),
('camera_matrix', 'camera_matrix'),
('distortion_vector', 'distortion_vector'),
)

_persist = 'single_laser PATTERN_MATRIX_SIZE PATTERN_SQUARE_SIZE PATTERN_ORIGIN ui_base_i UI_RATIO VIDEO_DEVICE SERIAL_DEVICE SERIAL_SPEED ROTATE ROI SYNC_FRAME_FAST SYNC_FRAME_STD BLUR'.split()
_algos_p = 'denoise threshold'.split()

# Possible persistent
single_laser = 0

PATTERN_MATRIX_SIZE = (11, 6)
PATTERN_SQUARE_SIZE = 13.0
PATTERN_ORIGIN = 38.9 # distance plateau to second row of pattern

ui_base_i = 2 # UI speed factor

# algo settings
algo_threshold = 8
algo_denoise = 2

UI_RATIO = 0.8
VIDEO_DEVICE = ""
SERIAL_DEVICE = ""
SERIAL_SPEED = 115200

ROTATE = 3 # 0=None, 1=90, ... counter-clockwise
LASER_COUNT = 2
ROI = (100, 150)

SYNC_FRAME_FAST = 1
SYNC_FRAME_STD = 3

BLUR = 3

# Non persistent

SEGMENTATION_METHOD = 'pureimage'

skip_calibration = True
interactive_calibration = False
configuration = 'thot'
pure_mode = False

def get_pattern_points():
    pattern_points = np.zeros((np.prod(PATTERN_MATRIX_SIZE), 3), np.float32)
    pattern_points[:, :2] = np.indices(PATTERN_MATRIX_SIZE).T.reshape(-1, 2)
    return np.multiply(pattern_points, PATTERN_SQUARE_SIZE)

WORKDIR="./capture"
CALIBDIR="./calibration"
SHOTSDIR="./screenshots"
FILEFORMAT='jpg' # or png

CONF_DIR = os.path.expanduser('~/.config/thot')

for d in (WORKDIR, CALIBDIR, SHOTSDIR, CONF_DIR):
    try: os.mkdir(d)
    except: pass

CAMERA_SETTINGS_FILE = os.path.join(CONF_DIR, 'cam_data.bin')
PROFILE_SETTINGS_FILE = os.path.join(CONF_DIR, 'profile.bin')

try:
    prof = pickle.load(open(PROFILE_SETTINGS_FILE, 'rb'))
except Exception:
    pass
else:
    g = globals()
    for k, v in prof.items():
        g[k] = v

def save_profile():
    g = globals()
    d = {}
    for k in _persist:
        d[k] = g[k]
    for k in _algos_p:
        k = "algo_"+k
        d[k] = g[k]
    pickle.dump(d, open(PROFILE_SETTINGS_FILE, 'wb'))

class Attribute(dict):

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __repr__(self):
        s = []
        it = list(self.items()) + list(self.__dict__.items())
        it.sort()
        for v in it:
            s.append("%s=%s"%v)
        return "<%s>"%(', '.join(s))

def _cast(val):
    if isinstance(val, (list, tuple)):
        val = np.array(val)
    return val

def get_laser_range():
    if single_laser == 0:
        return range(LASER_COUNT)
    else:
        return [single_laser-1]

def load_data(calibration_data):
    src = _from_horus() if configuration[0] == 'h' else  pickle.load( open(CAMERA_SETTINGS_FILE, 'rb'))
    for n in ('platform_rotation', 'platform_translation', 'camera_matrix', 'distortion_vector', 'laser_planes'):
        setattr(calibration_data, n, _cast(src[n]))
    return calibration_data

def save_data(s, clean=True):
    if not clean:
        s = {
        'distortion_vector': s._distortion_vector,
        'camera_matrix': s._camera_matrix,

        'platform_translation': s.platform_translation,
        'platform_rotation': s.platform_rotation,

        'laser_planes': s.laser_planes,
        }
    pickle.dump(s, open(CAMERA_SETTINGS_FILE, 'wb'))

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
        m = repr(m.round(3))[5:]
        m = m[1:1+m.rindex(']')]
    except Exception:
        return str(m)
    else:
        return str(eval(m))

def import_val(what=None):
    " Imports some configuration from horus "
    h = _from_horus()
    o =  pickle.load( open(CAMERA_SETTINGS_FILE, 'rb'))
    if what is None:
        for k in o.keys():
            print(" - %s"%k)
        return
    o[what] = h[what]
    save_data(o, clean=True)

def compare():
    " Display horus & thot configurations side by side "
    settings = _from_horus()
    o =  pickle.load( open(CAMERA_SETTINGS_FILE, 'rb'))
    SEP="\n"
    print("HORUS"+SEP+"THOT")
    for n in ('platform_rotation', 'platform_translation', 'camera_matrix', 'distortion_vector', 'laser_planes'):
        print(">>>> %s ::"%(n))
        v1 = settings[n]
        v2 = o[n]
        if n != 'laser_planes':
            v1 = _view_matrix(v1)
            v2 = _view_matrix(v2)
        print("%s%s%s"%(v1 , SEP, v2))

def get_serial_list():
    """Obtain list of serial devices"""
    baselist = []
    for device in ['/dev/ttyACM*', '/dev/ttyUSB*', '/dev/tty.usb*', '/dev/tty.wchusb*',
                   '/dev/cu.*', '/dev/rfcomm*']:
        baselist = baselist + glob.glob(device)
    return baselist

