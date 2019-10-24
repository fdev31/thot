# A Ciclop 3D Scanner CLI

## Introduction

I got a Ciclop 3D scanner, figured it can't work well on modern Linux distributions, started to hack...

This scanner is fully opensource, uses double lasers and is quite decent for the price.
You can find some for [around $100](https://fr.aliexpress.com/w/wholesale-ciclop.html?initiative_id=SB_20161008042416&site=fra&groupsort=1&SortType=price_asc&g=y&SearchText=ciclop) on the web.
This software only targets Linux users.

## Features

- Makes any scanner work on Linux (currently Ciclop is supported, any can be added in few hours)
- Colored two lasers scanning done in 2.5 minutes (in bright condition)
- Fully automated calibration done in 30s !
- Manual laser segmentation mode (to avoid calibration mistakes)
- Two passes scanning mode for difficult objects
- User friendly CLI

## Installation

On Archlinux system:

    % yaourt -S --needed opencv python-numpy python-scipy
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

Calibrate software (after changing exposure to get the pattern recognized):

    Scan Bot> cam_exposure 3000
    Scan Bot> calibrate

Scan 3D object

    Scan Bot> scan

## Advanced usages

From the shell you can enable more commands using **advanced** command, the most useful is probably the **cfg** command.

You can also call the application from the command line:

    $ thot recalibrate

Reconstruct previously scanned mesh (to test new calibration):

    $ thot make

A special "exec" command allows command chaining from the command line:

    $ thot exec calibrate, keep_laser 1 , make

Rebuild mesh from previous scan, keeping first laser information only:

    $ thot exec keep_laser 1, make

Rebuild mesh with different line detection threshold

    $ thot exec algop threshold 5, make

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

    Scan Bot> advanced
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
You can fix it by discarding the frames that are not well analyzed:

    $ thot recalibrate_manual

In case you want to capture the pictures again, just type:

    $ thot calibrate_manual

## If I keep only one lazer I get good results, but with two I have "mirrored" point clouds

The angles are probably inverted.
Try reversing your motor wires and retry.

## Bugs

- no release yet: may not work out of the box, consider unstable
- camera value getters are broken
- opencv changed, a quick fix has been done to use it in the mainthread but a bigger refactor would be required
