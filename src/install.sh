#!/bin/bash


if [[ -z $(python3 --version) ]]
then
    sudo apt update
    sudo apt install python3
    echo '====  PYTHON3 INSTALLED  ===='
fi

# sudo apt-get update
# sudo apt-get install build-essential
sudo apt update
sudo apt install python3-pip
pip3 install pyserial
pip3 install numpy
pip3 install tqdm
pip3 install PyQt5
pip3 install pyqtgraph
sudo apt update
sudo apt install qtbase5-dev qt5-qmake
# sudo apt install sofrware-properties-qt
sudo pip3 install pyinstaller



sudo adduser $USER dialout

sudo touch /etc/udev/rules.d/50-myusb.rules

# sudo sed "KERNEL==\"usbtmc[0-9]*\",MODE=\"0666\"" /etc/udev/rules.d/50-myusb.rules
sudo chmod 777 /etc/udev/rules.d/50-myusb.rules
sudo echo "KERNEL==\"usbtmc[0-9]*\",MODE=\"0666\"" >> /etc/udev/rules.d/50-myusb.rules
sudo reboot



