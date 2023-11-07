
from Xeryon import *
from pylablib.devices import Ophir
import rigol2000a

import serial
import time

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout,  QCheckBox, QHBoxLayout, QLabel, QFrame, QLineEdit, QComboBox
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QThread, QObject, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFont

from pyqtgraph import PlotWidget, plot
from pyqtgraph.Qt import QtGui
import pyqtgraph as pg

import sys
from glob import glob
from os import system
import re
from threading import Thread


from pathlib import Path


class MainWindow(QtWidgets.QMainWindow):

    def __del__(self):
        if self.is_xeryon_exist == 1:
            self.axisX.reset()
            self.controller.stop()
        # self.vega.close()
        # self.timer.stop()
        # self.termal_timer.stop()

    def closeEvent(self, event):
        ret = QtWidgets.QMessageBox.warning(None, 'Внимание!', 'Лазер Выключен?',
                                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                            QtWidgets.QMessageBox.Yes)
        if ret == QtWidgets.QMessageBox.Yes:
            self.termal_send_command("disable")
            QtWidgets.QMainWindow.closeEvent(self, event)
        else:
            QtWidgets.QMainWindow.closeEvent(self, event)
            # event.ignore()

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.Xeryon_cbox = QCheckBox("Двигатель")
        self.Termal_cbox = QCheckBox("Охлаждение лазера")
        self.Rigol_cbox = QCheckBox("Осцилограф")

        self.Xeryon_cbox.setCheckable(False)
        self.Termal_cbox.setCheckable(False)
        self.Rigol_cbox.setCheckable(False)

        device_list_layout = QHBoxLayout()
        device_list_layout.addWidget(self.Xeryon_cbox)
        device_list_layout.addWidget(self.Termal_cbox)
        device_list_layout.addWidget(self.Rigol_cbox)

        self.graphWidget = pg.PlotWidget()
        self.graphWidget.setBackground('w')
        # Add Axis Labels
        styles = {"color": "#000", "font-size": "20px"}
        self.graphWidget.setLabel("left", "Интенсивность (у:е)", **styles)
        self.graphWidget.setLabel("bottom", "Волновое число", **styles)
        # Add grid
        self.graphWidget.showGrid(x=True, y=True)
        self.graphWidget.plotItem.setMouseEnabled(x=False)
        self.graphWidget.plotItem.setMouseEnabled(y=False)

        font = QtGui.QFont()
        font.setPixelSize(20)
        self.graphWidget.getAxis("bottom").setTickFont(font)
        self.graphWidget.getAxis("left").setTickFont(font)

        pen = pg.mkPen(color=(0, 255, 0), width=8, style=QtCore.Qt.SolidLine)

        self.data_line = self.graphWidget.plot(
            self.x, self.y, name="my plot",  pen=pen)

        self.angles = self.from_file_to_list("sort_angles.txt")
        self.wave_numbers = self.from_file_to_list("wave_numbers.txt")

        # self.init_Xeryon("/dev/ttyACM0")
        # self.init_Vega("/dev/ttyUSB1")
        # self.init_Rigol()
        self.ser = self.init_termal("/dev/ttyUSB0")

        self.timer = QtCore.QTimer()
        self.timer.setInterval(3000)
        self.timer.timeout.connect(self.update_plot)
        # self.timer.setInterval(21000)
        # self.timer.timeout.connect(self.save_data_to_file)

        self.termal_timer = QtCore.QTimer()
        # # self.termal_timer.setInterval(15000)
        # self.termal_timer.timeout.connect(self.update_termal_status)
        self.termal_timer.start()

        start_button = QPushButton("СТАРТ")
        start_button.clicked.connect(self.start_button_clicked)

        stop_button = QPushButton("СТОП")
        stop_button.clicked.connect(self.stop_button_clicked)

        self.label_status = QLabel("")
        self.label_status.setFrameStyle(QFrame.Panel | QFrame.Sunken)

        layout = QVBoxLayout()
        layout.addLayout(device_list_layout)
        layout.addWidget(self.graphWidget)

        # START
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

        # STOP
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
        self.step_choice = QComboBox(self)
        self.step_choice.addItem("Выбор Шага(0.05 по умолчанию):")
        self.step_choice.addItem("0.05")
        self.step_choice.addItem("0.1")
        self.step_choice.addItem("0.5")
        self.step_choice.addItem("1")
        set_ang_button = QPushButton("Установить угол")
        set_ang_button.clicked.connect(self.set_ang_button_clicked)
        save_to_file_button = QPushButton("Сохранить данные в файл")
        save_to_file_button.clicked.connect(self.save_data_to_file)
        self.set_ang_line_edit = QLineEdit("101.1")
        self.label_cur_vcc = QLabel("")
        self.label_cur_vcc.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        set_ang_layout.addWidget(self.step_choice)
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

        self.termal_on_button_clicked()
        # self.update_termal_status()

    is_xeryon_exist = 0

    def init_Xeryon(self, device_name):
        # device_file = Path(device_name)
        if Path(device_name).exists():
            self.controller = Xeryon(device_name, 115200)
            self.axisX = self.controller.addAxis(Stage.XRTU_30_109, "X")
            self.controller.start()
            self.axisX.findIndex()
            self.axisX.setUnits(Units.deg)
            self.is_xeryon_exist = 1
            self.Xeryon_cbox.setChecked(True)

    def init_Vega(self, device_name):
        if Path(device_name).exists():
            self.vega = Ophir.VegaPowerMeter(device_name, 9600)

    def init_Rigol(self):
        if glob('/dev/usbtmc*'):
            self.Rigol_cbox.setChecked(True)
            self.osc = rigol2000a.Rigol2072a()
            # Change voltage range of channel 1 to 50mV/div.
            self.osc[2].set_vertical_scale_V(0.02)

    x_value = []
    y_value = []

    def intergal_per_area(self):
        # self.osc[2].get_data('norm', 'channel%i.dat' % 2)
        self.get_data_for_integral("channel2.dat")

        summ = 0
        for indx in range(len(self.x_value) - 1):
            half = (float(self.x_value[indx]) -
                    float(self.x_value[indx + 1])) / 2

            step = float(self.y_value[indx]) + float(self.y_value[indx + 1])
            summ += half * step
        if summ < 0:
            summ *= -1

        print(summ)
        return summ

    def get_data_for_integral(self, filemane):
        file1 = open(filemane, 'r')
        Lines = file1.readlines()
        for line in Lines:
            # value before comma exept comma
            self.x_value.append(''.join(re.findall("^(.+?),", line)))
            # value after comma except comma
            self.y_value.append(''.join(re.findall("^(.+?),", line)))

    def from_file_to_list(self, filemane):
        list = []
        file1 = open(filemane, 'r')
        Lines = file1.readlines()

        for line in Lines:
            list.append(line)

        # for i in range(len(list)):
        #     print(list[i])
        return list

    epos = 0
    dpos = 0
    step = 0.05
    value = []
    stop_do_it = 0

    def save_data_to_file(self):

        file = open("user_data.txt", "w+")
        for index in range(len(self.angles)):
            st = str(float(self.wave_numbers[index])) + \
                " " + str(float(self.angles[index])) + "\n"
            file.write(st)
        file.close()

        # experiment
        # if not self.stop_do_it:
        #     self.axisX.setDPOS(self.cur_ang)
        #     for i in range(0, 100):
        #         self.value.append(float(self.osc[2].get_vpp()) * float(1000))
        #         time.sleep(0.2)
        #         # i += 1

        #     filename = "./test/" + str(float(self.axisX.getEPOS())) + "_" + str(round(float(self.cur_ang), 2)) + ".txt"

        #     file = open(filename, "w")
        #     for index in range(100):
        #         st = str(float(self.value[index])) + "\n"
        #         file.write(st)
        #     file.close()

        #     self.cur_ang -= self.step
        #     self.value.clear()

        #     if self.cur_ang < round(float(93), 2):
        #         self.value.clear()
        #         self.stop_do_it = 1

    def set_ang_button_clicked(self):
        if self.is_xeryon_exist == 1:
            self.axisX.setDPOS(self.set_ang_line_edit.text())
            if (self.device_choice.currentText() == "RIGOL Oscilloscope"):
                self.label_cur_vcc.setText(
                    "Интенсивность: " + str(round((float(self.osc[2].get_vpp()) * float(1000)), 2)) + " у:е")
            else:
                time.sleep(3)
                self.label_cur_vcc.setText(
                    "Мощность: " + str(round((float(self.vega.get_power()) * float(1000)), 2)) + " мВт")

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

    # def under_plot_area(self):

    def start_button_clicked(self):
        if self.is_xeryon_exist == 1:
            if re.findall("\d+\.\d+", str(self.start_line_edit.text())) == "" or re.findall("\d+\.\d+", str(self.stop_line_edit.text())) == "":
                self.label_status.setText("Введите число в фромате dddd.dddd")
                time.sleep(1)
            else:
                self.axisX.setDPOS(float(self.start_line_edit.text()))
                self.cur_ang = float(self.axisX.getDPOS())
                self.timer.start()
                self.wave_indx = 0
                self.x.clear()
                self.y.clear()
                self.stop_plot = 1
                print(self.stop_plot)
                self.stop_do_it = 0

    def stop_button_clicked(self):
        self.intergal_per_area()
        self.timer.stop()
        if self.is_xeryon_exist == 1:
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

    i = 0

    def update_plot(self):
        if self.stop_plot == 0:
            self.timer.stop()
        else:
            # print("cur_ang ", self.cur_ang)

            # is_good_angle = self.binary_search(self.angles, 0, len(self.angles)-1, round(self.cur_ang, 2))
            is_good_angle = 1
            if is_good_angle != -1:
                self.axisX.setDPOS(self.cur_ang)
              #
                time.sleep(0.1)
              # Rigol or Vega
                # self.x.append(float(self.wave_numbers[self.wave_indx]))

                # if (self.device_choice.currentText() == "RIGOL Oscilloscope"):
                #     self.y.append(float(self.osc[2].get_vpp()) * float(1000))
                # else:
                #     time.sleep(3)
                #     self.y.append(float(self.vega.get_power()) * float(1000))

                # self.data_line.setData(self.x, self.y)
              ####
                self.wave_indx += 1

            if self.step_choice.currentText() != "Выбор Шага(0.05 по умолчанию):":
                self.cur_ang -= round(float(self.step_choice.currentText()), 2)
            else:
                self.cur_ang -= 0.05

            # if self.wave_indx > 140 or round(self.cur_ang, 2) < round(float(self.stop_line_edit.text()), 2):
            #     self.stop_plot = 0
            if round(self.cur_ang, 2) < round(float(self.stop_line_edit.text()), 2):
                self.stop_plot = 0

# ---------Termal-------------
    termal_enable_status = 0
    is_termal_exist = 0

    def termal_on_button_clicked(self):
        self.termal_timer.start()
        self.termal_send_command("enable")
        self.termal_enable_status = 1

    def termal_off_button_clicked(self):
        self.termal_timer.stop()
        self.termal_send_command("disable")
        self.termal_enable_status = 0

    def update_termal_status(self):
        # self.termal_send_command("gsoll")
        self.termal_send_command("gist")
        # self.termal_send_command("ps")

    def init_termal(self, device_name):
        # device_file = Path(device_name)
        if Path(device_name).exists():
            self.Termal_cbox.setChecked(True)
            SERIALPORT = device_name
            BAUDRATE = 115200
            ser = serial.Serial(SERIALPORT, BAUDRATE)
            ser.bytesize = serial.EIGHTBITS  # number of bits per bytes
            ser.parity = serial.PARITY_NONE  # set parity check: no parity
            ser.stopbits = serial.STOPBITS_ONE  # number of stop bits
            ser.timeout = 2  # timeout block read
            ser.writeTimeout = 0  # timeout for writereturn ser
            self.is_termal_exist = 1
            return ser

    def termal_send_command(self, command):
        if self.is_termal_exist == 1:
            str_temp = ""
            current_temp = ""
            desire_temp = ""
            enable_status = ""
            if not self.ser.isOpen():
                self.ser.open()

            if self.ser.isOpen():

                try:
                    self.ser.flushInput()  # flush input buffer, discarding all its contents
                    self.ser.flushOutput()  # flush output buffer, aborting current output

                    # command = command + '\r'
                    self.ser.write((command + '\r').encode('ascii'))

                    time.sleep(0.5)

                    # time.sleep(0.5)
                    numberOfLine = 0

                    print("start reading")
                    print("my command = " + command)
                    while True:
                        response = self.ser.readline().decode('utf-8', errors='ignore')
                        print("----read data: " + response)
                        if (response == '' or numberOfLine > 5):
                            print("finish reading")
                            break

                        if command == 'gist':
                            current_temp = re.findall("\d+\.\d+", response)
                        numberOfLine = numberOfLine + 1

                    self.ser.close()

                except Exception as e:
                    print("error communicating...: " + str(e))

            else:
                print("cannot open serial port ")

            if str_temp != "01 ERROR":
                str_temp = "Температура лазера= " + \
                    ''.join(current_temp) + " С || " + \
                    "Установленная температура лазера = 18"
                if self.termal_enable_status == 1:
                    str_temp += " С || Охлаждение Включено"
                else:
                    str_temp += " С || Охлаждение Выключено"
            else:
                str_temp = "01 ERROR"
            self.label_status.setText(str_temp)


########################
app = QtWidgets.QApplication(sys.argv)
w = MainWindow()
w.show()
sys.exit(app.exec_())
