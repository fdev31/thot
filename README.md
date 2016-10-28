# A Ciclop 3D Scanner CLI

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
- fully automated calibration done in a minute

Watch [introduction video](https://youtu.be/qUJCSKR_FXM)

## Help wanted!

To find why the two point clouds are slightly deformed, probably I'm missing some math in calibration...

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

Calibrate software:

    Scan Bot> view
    # You can change the camera settings with set* commands to get a stable pattern displayed
    Scan Bot> setGain 5
    Scan Bot> setExposureAbsolute 3000
    Scan Bot> calibrate

Scan 3D object

    Scan Bot> scan

## Advanced usages

You can also call the application from the command line:

    $ ./thot recalibrate

Reconstruct previously scanned mesh (to test new calibration):

    $ ./thot make

A special "exec" command allows command chaining from the command line:

    $ ./thot exec setGain 5, calibrate, keep_laser 1 , make

Rebuild mesh from previous scan, keeping first laser information only:

    $ ./thot exec keep_laser 1, make

Recalibrate manually (while calibrating laser some lines are not matching the picture)

    $ ./thot exec recalibrate_manual, recalibrate


Images are saved into **capture/** folder
Pointcloud is saved as **capture.ply**

## Example

![Scanned model](http://scan.crava.ch/shot.jpg)

## Future / TODO

- Improve platform calibration (very fragile algorithm :/)
- Blender integration
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

