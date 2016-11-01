
class CameraControl:

    _exposure = int(1000/30)

    def __init__(self, cap):
        cap.start()
        self.cap = cap
        self.exposure = self._exposure # unsupported

    def get_brightness(self):
        return self._brightness

    def set_brightness(self, value):
        self._brightness = self.cap.set_brightness(int(value))

    brightness = property(get_brightness, set_brightness)

class Board(object):
    def __init__(self, parent=None, serial_name='/dev/ttyUSB0', baud_rate=115200):
        pass

    def connect(self):
        pass

    def disconnect(self):
        pass

    def motor_speed(self, value):
        pass

    def motor_acceleration(self, value):
        pass

    def motor_enable(self):
        pass

    def motor_disable(self):
        pass

    def motor_reset_origin(self):
        pass

    def motor_move(self, step=0, nonblocking=False, callback=None):
        pass

    def laser_on(self, index):
        pass

    def laser_off(self, index):
        pass

    def lasers_on(self):
        pass

    def lasers_off(self):
        pass
