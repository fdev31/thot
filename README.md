# A Ciclop 3D Scanner CLI

## Introduction

I got a Ciclop 3D scanner, figured it can't work well on modern Linux distributions, started to hack...

This scanner is fully opensource, uses double lasers and is quite decent for the price.
You can find some for [around $100](https://fr.aliexpress.com/w/wholesale-ciclop.html?initiative_id=SB_20161008042416&site=fra&groupsort=1&SortType=price_asc&g=y&SearchText=ciclop) on the web.
This software only targets Linux users.

## Features

- Make Ciclop scanner work on Linux with standard OpenCV
- Colored two lasers scanning done in 4 minutes
- Fully automated calibration done in 30s !
- Manual laser segmentation mode (to avoid calibration mistakes)
- Two passes scanning mode for difficult objects
- User friendly CLI


## Help wanted!

To find why the two point clouds are slightly deformed, probably I'm missing some math in calibration...

## Installation

On archlinux system:

    % yaourt -S opencv python-v4l2capture python-numpy libwebcam python-scipy
    % wget https://github.com/fdev31/thot/archive/master.zip
    % unzip master.zip
    % cd thot-master
    % python setup.py build
    % sudo python setup.py install

> If you prefer using python2, just replace "python" with "python2" on the lines above

> You may also want to install *guvcview* to setup the webcam before starting the app

## Usage

[![Quickstart video](https://img.youtube.com/vi/qUJCSKR_FXM/0.jpg)](https://www.youtube.com/watch?v=qUJCSKR_FXM)

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

    $ thot recalibrate

Reconstruct previously scanned mesh (to test new calibration):

    $ thot make

A special "exec" command allows command chaining from the command line:

    $ thot exec setGain 5, calibrate, keep_laser 1 , make

Rebuild mesh from previous scan, keeping first laser information only:

    $ thot exec keep_laser 1, make

Recalibrate the laser manually (don't reshot the patter, just re-analyse asking for you to discard wrong lines)

    $ thot exec calibrate_manual, recalibrate

Rebuild mesh with different line detection algorithm

    $ thot algorithm pureimage, make

Images are saved into **capture/** folder
Pointcloud is saved as **capture.ply**

## Example

Result of a 2 lasers scan (unprocessed point cloud):

![Tux](http://scan.crava.ch/tux.png)
![Tux side](http://scan.crava.ch/tux_side.png)

## Future / TODO

- Make "first start" commands:
    - make separate shots for camera
    - calibrate camera from the shots
    - ask user to place the pattern on the surface
    - start calibration
- Blender integration
- compute normals or mesh directly

## Dependencies

- opencv
- numpy
- pyserial
- prompt_toolkit
- scipy

# Troubleshooting

## "Mesh in a mesh" issue

If you have a mesh inside another mesh, this is probably a camera calibration issue:
take many shots with the `shot` command (changing position of chessboard each time to cover maximum surface), then use `calibrate_shots` to compute camera calibration again.

    Scan Bot> shot
    Scan Bot> shot
    Scan Bot> shot
    Scan Bot> shot
    Scan Bot> shot
    Scan Bot> calibrate_shots

After this you will need to do standard calibration again (platform and lasers), in case you didn't change the setup and you calibrated the scanner recently, you can avoid capturing pictures by typing:

    $ thot recalibrate

## Meshe is randomly distorted, but I can see two different shapes

This is probably a laser calibration issue, some lines are probably badly detected.
You can fix it by discarding the frames that are not well analysed:

    $ thot exec recalibrate_manual, recalibrate

In case you want to capture the pictures again, just type:

    $ thot exec recalibrate_manual, calibrate

## Bugs

- no release yet: may not work out of the box, consider unstable
- camera value getters are broken
- No easy way to change video & serial device in case it's not detected correctly

