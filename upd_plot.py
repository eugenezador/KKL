
from Xeryon import *
from pylablib.devices import Ophir
import rigol2000a

import serial, time

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QLabel, QFrame, QLineEdit
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QObject, QThread, pyqtSignal

from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg

import sys
# import random
import re
from threading import Thread


class CorrSpectr(QThread):
    def __init__(self, mainwindow, parent = None):
        super().__init__()
        self.mainwindow = mainwindow

    def run(self):
        intesity = QSpinBox.value(self.mainwindow.spin_intensity)
        inttime = QSpinBox.value(self.mainwindow.spin_inttime)
        self.mainwindow.install_spectr('sample',1)
        ans,[wavelengths, intensities] = correletions(intesity,inttime)
        QLabel.setText(self.mainwindow.lb_correlation, str(ans))
        self.mainwindow.standard.setData(wavelengths, intensities)



class MainWindow(QtWidgets.QMainWindow):    
    
    index = 0
    angles = []
    wave_numbers = []
    Y_data = []

    x = []
    y = []


    termal_name = "/dev/ttyUSB0"

    def __del__(self):
        self.axisX.reset()
        self.controller.stop()
        # self.vega.close()

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.graphWidget = pg.PlotWidget()
        # self.setCentralWidget(self.graphWidget)

        
        self.angles = self.from_file_to_list("angles.txt")
        self.wave_numbers = self.from_file_to_list("wave_numbers.txt")


        self.init_Xeryon("/dev/ttyACM0")
        # self.init_Vega("/dev/ttyUSB1")
        self.init_Rigol()
        self.ser = self.init_termal("/dev/ttyUSB0")

        self.graphWidget.setBackground('w')
        self.data_line =  self.graphWidget.plot(self.x, self.y)



        termal_button = QPushButton("termal")
        termal_button.clicked.connect(self.termal_button_clicked)
        self.label_status = QLabel("")
        self.label_status.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.termal_line_edit = QLineEdit("ps")

        start_button = QPushButton("START")
        start_button.clicked.connect(self.start_button_clicked)
        stop_button = QPushButton("STOP")
        stop_button.clicked.connect(self.stop_button_clicked)


        # self.timer = QtCore.QTimer()
        # self.timer.setInterval(500)
        # self.termal_send_command("ps")
        # self.termal_send_command("disable")
        # self.timer.timeout.connect(self.update_plot)
        # self.timer.start()


        layout = QVBoxLayout()
        
        
        layout.addWidget(self.graphWidget)
        layout.addWidget(termal_button)
        layout.addWidget(start_button)
        layout.addWidget(stop_button)
        
        layout.addWidget(self.termal_line_edit)
        layout.addWidget(self.label_status)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)


    def init_Xeryon(self, device_name):
        self.controller = Xeryon(device_name, 115200)
        self.axisX = self.controller.addAxis(Stage.XRTU_30_109, "X")
        self.controller.start()
        self.axisX.findIndex()


    def init_Vega(self, device_name):
        self.vega = Ophir.VegaPowerMeter((device_name, 9600))


    def init_Rigol(self):
        self.osc = rigol2000a.Rigol2072a()

        # Change voltage range of channel 1 to 50mV/div.
        self.osc[2].set_vertical_scale_V(0.02)

    def from_file_to_list(self, filemane):
        list = []
        file1 = open(filemane, 'r')
        Lines = file1.readlines()
 
        for line in Lines:
            list.append(line)

        # for i in range(len(self.angles)):
        #     print(self.angles[i])
        return list

    
    def start_button_clicked(self):
        # power = []
        # epos = []
        print("START")
        self.axisX.setUnits(Units.deg)
        self.axisX.setDPOS(118.95)
        is_goog_angle = 0
        cur_ang = float(self.axisX.getDPOS())

        wave_indx = 0
        for i in range(0, 30):

            print("cur_ang ", cur_ang)
            for j in range (0, len(self.angles)):
                if round(float(cur_ang), 2) == round(float(self.angles[j]), 2):
                    print("angles[j] ", self.angles[j])
                    is_good_angle = 1
                    break
                else:
                    is_good_angle = 0

           
            if is_good_angle == 1 and wave_indx < 140:
                self.axisX.setDPOS(cur_ang)
                vpp = float(self.osc[2].get_vpp())
                vpp *= float(1000)
                print("wave_indx")
                print(wave_indx)

                ###
                self.x.append(float(self.wave_numbers[wave_indx])) 
                self.y.append(float(vpp))
                self.data_line.setData(self.x, self.y)
                ####

                # self.update_plot(float(self.wave_numbers[wave_indx]), float(vpp))
                wave_indx += 1
                # epos.append(self.axisX.getEPOS())
                time.sleep(1)

            cur_ang -= 0.05
            # cur_ang = round(cur_ang, 2)
            # print(cur_ang)

    def update_plot(self, x_data, y_data):
        self.x.append(x_data) 
        self.y.append(y_data)
        self.data_line.setData(self.x, self.y)

    def stop_button_clicked(self):
        self.axisX.reset()
        self.controller.stop()
        # self.vega.close()

    def termal_button_clicked(self):
        # self.termal_send_command("ps")
        self.termal_send_command(self.termal_line_edit.text(),self.termal_name)



    def init_termal(self, device_name):
        SERIALPORT = device_name
        BAUDRATE = 115200

        ser = serial.Serial(SERIALPORT, BAUDRATE)

        ser.bytesize = serial.EIGHTBITS #number of bits per bytes

        ser.parity = serial.PARITY_EVEN #set parity check: no parity

        ser.stopbits = serial.STOPBITS_ONE #number of stop bits

        #ser.timeout = None          #block read

        #ser.timeout = 0             #non-block read

        ser.timeout = 2              #timeout block read

        ser.xonxoff = True     #disable software flow control

        ser.rtscts = False     #disable hardware (RTS/CTS) flow control

        ser.dsrdtr = False       #disable hardware (DSR/DTR) flow control

        ser.writeTimeout = 0     #timeout for write

        return ser

    def termal_send_command(self, command, device_name):

        self.ser = self.init_termal(device_name)

        str_temp = ""
        current_temp = ""
        desire_temp = ""
        enable_status = ""

        if self.ser.isOpen():

            try:
                self.ser.flushInput() #flush input buffer, discarding all its contents
                self.ser.flushOutput()#flush output buffer, aborting current output

                # ser.write(b"ps\r")
                command = command + '\r'
                command = str.encode(command)
                self.ser.write(command)
                # print("write data: " + command)
                time.sleep(0.5)
                numberOfLine = 0

                while True:
                    response = self.ser.readline().decode('ascii', errors='ignore')
                    print("read data: " + response)


                    if "Ist" in response:
                        current_temp = re.findall("\d+\.\d+", response)
                                               

                    if "Soll" in response:
                        desire_temp = re.findall("\d+\.\d+", response)

                    if "Enable OK" in response:
                        enable_status = re.findall("(Yes|No)", response)
                        print(enable_status)

                    # if "01" in response:
                    #     str_temp = "01 ERROR"

                    numberOfLine = numberOfLine + 1
                    if (response == ''):
                        break
                self.ser.close()

            except Exception as e:
                print ("error communicating...: " + str(e))

        else:
            print ("cannot open serial port ")
        
        if str_temp != "01 ERROR":
            str_temp = "Current T = " + ''.join(current_temp) + " || " + "Desired T = " + ''.join(desire_temp) + "|| Enable = " + ''.join(enable_status)
        else:
            str_temp = "01 ERROR"
        self.label_status.setText(str_temp)
        # return status


########################
app = QtWidgets.QApplication(sys.argv)
w = MainWindow()
w.show()
sys.exit(app.exec_())
