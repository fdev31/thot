# A Ciclop 3D Scanner client

## Introduction

I got a Ciclop 3D scanner, figured it can't work well on modern Linux distributions, started to hack...

## Status

Not useful on its own yet since it requires you to first have performed the calibration using [Horus](https://github.com/bqlabs/horus).

In case someone is interested on my patches on Horus, making it work on unmodified opencv but slow as hell, just ask.

Useable for some people already, probably developers:

- Works on python 2.7+ & python 3
- No patched OpenCV needed
- Simple and friendly CLI

## Usage

After installing all dependencies, unpack sources and open a terminal emulator:

    % ./run.sh

Capture images:

    Scan Bot> capture


Convert images to .ply file:

    Scan Bot> analyse


Images are saved into **capture/** folder
Pointcloud is saved as **capture.ply**

## Future

If enough time...

- Automated calibration
- Blender integration
- Color support
- replace uvcdynctl by syscalls/ctypes/whatever
- find or write some blender extension to clean the pointcloud
- re-use older project to compute mesh from pointcloud automatically

## Dependencies

- Python (2 or 3)
- opencv
- numpy
- v4l2capture (check https://github.com/rmca/python-v4l2capture/tree/py3k for Python3 support)

For a few extra features (will be optional in the future):
- prompt_toolkit
- scipy
- libwebcam (*uvcdynctrl*)


## Bugs

- uses subprocess to set camera settings
- no release yet: may not work out of the box
- Exit of app not handled correctly (using ^C is quite mandatory after exit...)
- Bad timings when using Python3


