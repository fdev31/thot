#!/bin/sh
export PYTHONPATH="./src/"
# uncomment this line if you run into troubles launching thot:
#export PYTHONPATH=src:$(ls -1d build/lib.linux*)
python -m thotus.main $*
