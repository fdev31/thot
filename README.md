# A Ciclop 3D Scanner client

## Introduction

I got a Ciclop 3D scanner, figured it can't work well on modern Linux distributions, started to hack...

This scanner is fully opensource, uses double lasers and is quite decent for the price.
You can find some for [around $100](https://fr.aliexpress.com/w/wholesale-ciclop.html?initiative_id=SB_20161008042416&site=fra&groupsort=1&SortType=price_asc&g=y&SearchText=ciclop) on the web.
This software only targets Linux users.

## Status

Not giving very good calibration results yet, in heavy development.

Useable for some people already, probably developers:

- No patched OpenCV needed
- Simple and friendly CLI
- Python 2 & 3 compatible

## Installation

On archlinux system:

    % yaourt -S opencv python-v4l2capture python-numpy libwebcam python-scipy
    % wget https://github.com/fdev31/thot/archive/master.zip
    % unzip master.zip

> If you prefer using python2, just replace "python" with "python2" on the lines above

> You may also want to install *guvcview* to setup the webcam before starting the app

## Usage

After installing all dependencies, unpack sources and open a terminal emulator:

    % cd thot-master
    % ./run.sh

Capture images:

    Scan Bot> capture


Convert images to .ply file:

    Scan Bot> analyse


Images are saved into **capture/** folder
Pointcloud is saved as **capture.ply**

## Future / TODO


- Use computed plane ROI for laser segmentation
- Blender integration
- Color support
- replace uvcdynctl by a custom v4l2capture fork / ask the maintainer of py3k branch
- compute normals or mesh directly

## Dependencies

- Python (2 or 3)
- opencv
- numpy
- pyserial
- v4l2capture (check https://github.com/rmca/python-v4l2capture/tree/py3k for Python3 support)

For a few extra features (will be optional in the future):
- prompt_toolkit
- scipy
- libwebcam (*uvcdynctrl*)


## Bugs

- no release yet: may not work out of the box, consider unstable

