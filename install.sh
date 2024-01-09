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
pip3 install PyQt5
pip3 install pyqtgraph
sudo apt update
sudo apt install qtbase5-dev qt5-qmake
sudo pip3 install pyinstaller
