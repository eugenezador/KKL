
from Xeryon import *
from pylablib.devices import Ophir
import rigol2000a

import serial, time

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QLineEdit, QComboBox
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QThread, QObject, pyqtSignal, pyqtSlot

from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg

import sys
# import random
import re
from threading import Thread



class MainWindow(QtWidgets.QMainWindow):    

    def __del__(self):
        self.axisX.reset()
        self.controller.stop()
        self.vega.close()
        self.timer.stop()
        self.termal_timer.stop()

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        
        self.graphWidget = pg.PlotWidget()
        self.graphWidget.setBackground('w')
        # Add Axis Labels
        styles = {"color": "#000", "font-size": "20px"}
        self.graphWidget.setLabel("left", "Интенсивность (у:е)", **styles)
        self.graphWidget.setLabel("bottom", "Волновое число", **styles)
        #Add grid
        self.graphWidget.showGrid(x=True, y=True)
        self.graphWidget.plotItem.setMouseEnabled(x=False)
        self.graphWidget.plotItem.setMouseEnabled(y=False)

        pen = pg.mkPen(color=(0, 255, 0), width=8, style=QtCore.Qt.SolidLine)

        self.data_line =  self.graphWidget.plot(self.x, self.y, name="Sensor 1",  pen=pen)

        
        self.angles = self.from_file_to_list("sort_angles.txt")
        self.wave_numbers = self.from_file_to_list("wave_numbers.txt")


        # self.init_Xeryon("/dev/ttyACM0")
        # self.init_Vega("/dev/ttyUSB1")
        # self.init_Rigol()
        # self.ser = self.init_termal("/dev/ttyUSB0")

        self.timer = QtCore.QTimer()
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.update_plot)

        self.termal_timer = QtCore.QTimer()
        self.termal_timer.setInterval(15000)
        self.termal_timer.timeout.connect(self.update_termal_status)
        self.termal_timer.start()


        start_button = QPushButton("СТАРТ")
        start_button.clicked.connect(self.start_button_clicked)

        stop_button = QPushButton("СТОП")
        stop_button.clicked.connect(self.stop_button_clicked)

        self.label_status = QLabel("")
        self.label_status.setFrameStyle(QFrame.Panel | QFrame.Sunken)

        layout = QVBoxLayout()
        layout.addWidget(self.graphWidget)

        #START
        start_layout = QHBoxLayout()
        self.start_label = QLabel("Начальный угол: ")
        self.start_line_edit = QLineEdit("118.95")
        termal_on_button = QPushButton("ВКЛ. ОХЛАЖДЕНИЕ")
        termal_on_button.clicked.connect(self.termal_on_button_clicked)
        start_layout.addWidget(self.start_label)
        start_layout.addWidget(self.start_line_edit)
        start_layout.addWidget(start_button)
        start_layout.addWidget(termal_on_button)
        layout.addLayout(start_layout)
        
        #STOP
        stop_layout = QHBoxLayout()
        self.stop_label = QLabel("Конечный угол: ")
        self.stop_line_edit = QLineEdit("93")
        termal_off_button = QPushButton("ВЫКЛ. ОХЛАЖДЕНИЕ")
        termal_off_button.clicked.connect(self.termal_off_button_clicked)
        stop_layout.addWidget(self.stop_label)
        stop_layout.addWidget(self.stop_line_edit)
        stop_layout.addWidget(stop_button)
        stop_layout.addWidget(termal_off_button)
        layout.addLayout(stop_layout)

        # Set angle
        set_ang_layout = QHBoxLayout()
        set_ang_button = QPushButton("Установить угол")
        set_ang_button.clicked.connect(self.set_ang_button_clicked)
        save_to_file_button = QPushButton("Сохранить данные в файл")
        save_to_file_button.clicked.connect(self.save_data_to_file)
        self.set_ang_line_edit = QLineEdit("")
        self.label_cur_vcc = QLabel("")
        self.label_cur_vcc.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        set_ang_layout.addWidget(set_ang_button)
        set_ang_layout.addWidget(self.set_ang_line_edit)
        set_ang_layout.addWidget(self.label_cur_vcc)
        set_ang_layout.addWidget(save_to_file_button)

        layout.addLayout(set_ang_layout)
        layout.addWidget(self.label_status)
        # Device choice
        self.device_choice = QComboBox(self)
        self.device_choice.addItem("RIGOL Oscilloscope")
        self.device_choice.addItem("Ophir VEGA")
        layout.addWidget(self.device_choice)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)


    def init_Xeryon(self, device_name):
        self.controller = Xeryon(device_name, 115200)
        self.axisX = self.controller.addAxis(Stage.XRTU_30_109, "X")
        self.controller.start()
        self.axisX.findIndex()
        self.axisX.setUnits(Units.deg)


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

        # for i in range(len(list)):
        #     print(list[i])
        return list
    
    def save_data_to_file(self, x, y):
        i = 0
        with open("user_data.txt", "w") as txt_file:
            for line in x:
                if i == len(y) - 1:
                    break
                txt_file.write(" ".join(line) + " " + " ".join(y[i])+ "\n")
                i += 1
                
    

    def set_ang_button_clicked(self):
        self.axisX.setDPOS(self.set_ang_line_edit.text())

        if (self.device_choice.currentText() == "RIGOL Oscilloscope"):
            self.label_cur_vcc.setText("Интенсивность: " + str(round((float(self.osc[2].get_vpp()) * float(1000)), 2)) + " у:е")
        else:
            time.sleep(3)
            self.label_cur_vcc.setText("Мощность: " + str(round((float(self.vega.get_power()) * float(1000)), 2)) + " мВт")

    
    def binary_search(self, arr, low, high, x):
        if high >= low:
            mid = (high + low) // 2
            if round(float(arr[mid]), 2) == round(x, 2):
                return mid
            elif round(float(arr[mid]), 2) > round(x, 2):
                return self.binary_search(arr, low, mid - 1, x)
            else:
                return self.binary_search(arr, mid + 1, high, x)
        else:
            return -1
    
    def start_button_clicked(self):
        if re.findall("\d+\.\d+", str(self.start_line_edit.text())) == "" or re.findall("\d+\.\d+", str(self.stop_line_edit.text())) == "":
            self.label_status.setText("Введите число в фромате dddd.dddd")
            time.sleep(1)
        else:
            self.axisX.setDPOS(float(self.start_line_edit.text()))
            self.cur_ang = float(self.axisX.getDPOS())
            self.cur_ang = 200
            self.timer.start()
            self.wave_indx = 0
            self.x.clear()
            self.y.clear()
            self.stop_plot = 1

    def stop_button_clicked(self):
        self.timer.stop()
        self.axisX.reset()
        self.controller.stop()
        # self.vega.close()
        

    cur_ang = 0
    wave_indx = 0
    angles = []
    wave_numbers = []
    x = []
    y = []
    stop_plot = 0

    def update_plot(self):
        if self.stop_plot == 0:
            self.timer.stop()
        else:
            # print("cur_ang ", self.cur_ang)

            is_good_angle = self.binary_search(self.angles, 0, len(self.angles)-1, round(self.cur_ang, 2))

            if is_good_angle != -1:
                self.axisX.setDPOS(self.cur_ang)
              #
                time.sleep(0.1)
              #Rigol or Vega
                self.x.append(float(self.wave_numbers[self.wave_indx]))

                if (self.device_choice.currentText() == "RIGOL Oscilloscope"):
                    self.y.append(float(self.osc[2].get_vpp()) * float(1000))
                else:
                    time.sleep(3)
                    self.y.append(float(self.vega.get_power()) * float(1000))
              
                self.data_line.setData(self.x, self.y)
              ####
                self.wave_indx += 1

            self.cur_ang -= 0.05

            if self.wave_indx > 140 or round(self.cur_ang, 2) < round(float(self.stop_line_edit.text()), 2):
                self.stop_plot = 0

#---------Termal-------------
    termal_enable_status = 0
    def termal_on_button_clicked(self):
        # self.termal_timer.start()
        self.termal_send_command("enable")
        self.termal_enable_status = 1

    def termal_off_button_clicked(self):
        self.termal_timer.stop()
        self.termal_send_command("disable")
        self.termal_enable_status = 0

    def update_termal_status(self):
        self.termal_send_command("ps")


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

    def termal_send_command(self, command):

        # self.ser = self.init_termal(device_name)

        str_temp = ""
        current_temp = ""
        desire_temp = ""
        enable_status = ""
        if not self.ser.isOpen():
            self.ser.open()

        if self.ser.isOpen():

            try:
                self.ser.flushInput() #flush input buffer, discarding all its contents
                self.ser.flushOutput()#flush output buffer, aborting current output
                
                # self.ser.write(b"ps\r")
                command = command + '\r'
                command = str.encode(command)
                self.ser.write(command)
                # print("write data: " + command)
                time.sleep(0.5)

                time.sleep(0.5)
                numberOfLine = 0

                while True:
                    response = self.ser.readline().decode('ascii', errors='ignore')
                    print("read data: " + response)

                    if "Ist" in response:
                        current_temp = re.findall("\d+\.\d+", response)
                                               
                    if "Soll" in response:
                        desire_temp = re.findall("\d+\.\d+", response)

                    # if "Enable OK" in response:
                    #     enable_status = re.findall("(Yes|No)", response)
                    #     print(enable_status)

                    # if "01" in response:
                    #     str_temp = "01 ERROR"

                    numberOfLine = numberOfLine + 1
                    if (response == '' or numberOfLine > 5):
                        break
                    
                self.ser.close()

            except Exception as e:
                print ("error communicating...: " + str(e))

        else:
            print ("cannot open serial port ")
        
        if str_temp != "01 ERROR":
            str_temp = "Температура лазера= " + ''.join(current_temp) + "С || " + "Установленная температура лазера = " + ''.join(desire_temp)
            if self.termal_enable_status == 1:
                str_temp += "С || Охлаждение Включено"
            else:
                str_temp += "С || Охлаждение Выключено"
        else:
            str_temp = "01 ERROR"
        self.label_status.setText(str_temp)
        # return status


########################
app = QtWidgets.QApplication(sys.argv)
w = MainWindow()
w.show()
sys.exit(app.exec_())
