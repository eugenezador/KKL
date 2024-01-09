#!/bin/bash


# if [[ -z $(python3 --version) ]]
# then
    sudo apt update
    sudo apt install python3
#     echo '====  PYTHON3 INSTALLED  ===='
# fi

sudo apt update
sudo apt install python3-pip
pip3 install pyserial
pip3 install numpy
pip3 install tqdm