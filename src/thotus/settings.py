import pickle
import numpy

def load_data(calibration_data):
    o =  pickle.load( open('cam_data.bin', 'rb'))
    calibration_data.platform_translation = numpy.array(o['translation_vector'])
    calibration_data.platform_rotation = numpy.array(o['rotation_matrix'])
    calibration_data.camera_matrix = numpy.array(o['camera_matrix'])
    calibration_data.distortion_vector = numpy.array(o['distortion_vector'])
    return o

def save_data(s):
    pickle.dump(s, open('cam_data.bin', 'wb'))
