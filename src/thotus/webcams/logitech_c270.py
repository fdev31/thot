# -*- coding: utf-8 -*-

class CameraControl:
    def __init__(self, cap):
        self.cap = cap
        '''
        cap.set('gain', 128)
        cap.set('auto_white_balance', 0)
        cap.set('white_balance_temperature', 1)
        cap.set('exposure_auto', 1)
        cap.set('saturation', 20)
        cap.set('contrast', 32)
        '''
        self.brightness = 128
        self.exposure = 300
        cap.start()

    def get_brightness(self):
        return self._brightness

    def set_brightness(self, value):
        self._brightness = int(value)
#         self.cap.set_gain(self._brightness)

    brightness = property(get_brightness, set_brightness)

    def get_exposure(self):
        return self._exposure

    def set_exposure(self, value):
        self._exposure = self.cap.video.set_exposure_absolute(int(value))

    exposure = property(get_exposure, set_exposure)

