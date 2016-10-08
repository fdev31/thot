from v4l2 import *
import fcntl
import mmap
import select
import time

class Video_device:
    def __init__(self, devpath):
        vd = open(devpath, 'rb+', buffering=0)
        print("#"*80)
        print("#"*80)
        print("#"*80)
        print(" USING BROKEN CODE !!!")
        print(" FIX IT OR INSTALL v4l2 capture !!!")
        print(" - python2: available on pypi, install using pip")
        print(" - python3: https://github.com/rmca/python-v4l2capture/tree/py3k")
        print("#"*80)
        print("#"*80)
        print("#"*80)

        print(">> get device capabilities")
        cp = v4l2_capability()
        fcntl.ioctl(vd, VIDIOC_QUERYCAP, cp)

        print("Driver:", "".join((chr(c) for c in cp.driver)))
        print("Name:", "".join((chr(c) for c in cp.card)))

        fmt = v4l2_format()
        fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
        fcntl.ioctl(vd, VIDIOC_G_FMT, fmt)  # get current settings
        print("width:", fmt.fmt.pix.width, "height", fmt.fmt.pix.height)
        print("pxfmt:", "V4L2_PIX_FMT_YUYV" if fmt.fmt.pix.pixelformat == V4L2_PIX_FMT_YUYV else fmt.fmt.pix.pixelformat)
        print("bytesperline:", fmt.fmt.pix.bytesperline)
        print("sizeimage:", fmt.fmt.pix.sizeimage)
        fcntl.ioctl(vd, VIDIOC_S_FMT, fmt)  # set whatever default settings we got before

        parm = v4l2_streamparm()
        parm.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
        parm.parm.capture.capability = V4L2_CAP_TIMEPERFRAME
        fcntl.ioctl(vd, VIDIOC_G_PARM, parm)
        fcntl.ioctl(vd, VIDIOC_S_PARM, parm)  # just got with the defaults

        req = v4l2_requestbuffers()
        req.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
        req.memory = V4L2_MEMORY_MMAP
        req.count = 1  # nr of buffer frames
        fcntl.ioctl(vd, VIDIOC_REQBUFS, req)  # tell the driver that we want some buffers 

        self._v = vd
        self.fileno = vd.fileno

    def start(self):
        vd = self._v
        # setup a buffer
        buf = v4l2_buffer()
        buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
        buf.memory = V4L2_MEMORY_MMAP
        buf.index = 0
        fcntl.ioctl(vd, VIDIOC_QUERYBUF, buf)
        self.mm = mmap.mmap(vd.fileno(), buf.length, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=buf.m.offset)

        # queue the buffer for capture
        fcntl.ioctl(vd, VIDIOC_QBUF, buf)

        buf_type = v4l2_buf_type(V4L2_BUF_TYPE_VIDEO_CAPTURE)
        fcntl.ioctl(vd, VIDIOC_STREAMON, buf_type)

        t0 = time.time()
        max_t = 1
        ready_to_read, ready_to_write, in_error = ([], [], [])
        while len(ready_to_read) == 0 and time.time() - t0 < max_t:
            ready_to_read, ready_to_write, in_error = select.select([vd], [], [], max_t)

    def set_format(self, width, height, yuv):
        return width, height

    def queue_all_buffers(self):
        pass

    def read_and_queue(self):
        print(">read")
        vd = self._v
        buf = v4l2_buffer()
        buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
        buf.memory = V4L2_MEMORY_MMAP
        print("ioctl")
        fcntl.ioctl(vd, VIDIOC_DQBUF, buf)  # get image from the driver queue
        #print("buf.index", buf.index)
        data = self.mm.read()
        grey = bytes((bit for i, bit in enumerate(data) if not i % 2))
        color = bytes((bit for i, bit in enumerate(data) if i % 2))
        #vid.write(bytes((bit for i, bit in enumerate(mm.read()) if not i % 2)))  # convert yuyv to grayscale
        self.mm.seek(0)
        fcntl.ioctl(vd, VIDIOC_QBUF, buf)  # requeue the buffer
        return grey

    def create_buffers(self, num):
        return

    def close(self):
        del self.fileno
        fcntl.ioctl(self._v, VIDIOC_STREAMOFF, buf_type)
        self._v.close()

