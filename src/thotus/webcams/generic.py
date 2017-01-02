class CameraControl:
    def __init__(self, cap):
        self.cap = cap
        cap.start()

    def get_brightness(self):
        return self._brightness

    def set_brightness(self, value):
        self._brightness = int(value)

    brightness = property(get_brightness, set_brightness)

    def get_exposure(self):
        return 500
        #return self._exposure

    def set_exposure(self, value):
        self._exposure = int(value)

    exposure = property(get_exposure, set_exposure)

