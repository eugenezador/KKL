
from Xeryon import *
from pylablib.devices import Ophir
import rigol2000a

import serial
import time

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout,  QCheckBox, QHBoxLayout, QLabel, QFrame, QLineEdit, QComboBox
from PyQt5 import QtWidgets, QtCore

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


from PyQt5.QtCore import QThread, QObject, pyqtSignal as Signal, pyqtSlot as Slot


class Worker(QObject):
    progress = Signal(int)
    completed = Signal(int)
    is_working = False

    @Slot(int)
    def do_work(self, counter):
        while self.is_working:
            time.sleep(counter)
            print("in do work\n")
            print(self.is_working)
            self.progress.emit(counter)

        print("loop finished")
        self.completed.emit(counter)



class MainWindow(QtWidgets.QMainWindow):

    work_requested = Signal(int)
    termal_work_requested = Signal(int)

    def __del__(self):
        if self.is_xeryon_exist:
            self.axisX.reset()
            self.controller.stop()
        if self.is_Vega_exist:
            self.vega.close()

        self.termal_worker.is_working = False

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

        self.angles = self.from_file_to_list("angles.txt")
        self.wave_numbers = self.from_file_to_list("wave_numbers.txt")

        self.init_Xeryon("/dev/ttyACM0")
        self.init_Vega("/dev/ttyUSB1")
        self.init_Rigol()
        self.ser = self.init_termal("/dev/ttyUSB0")


        ################  WORKER  #################

        self.worker = Worker()
        self.worker_thread = QThread()

        self.worker.progress.connect(self.update_plot)
        self.worker.completed.connect(self.complete)

        self.work_requested.connect(self.worker.do_work)

        # move worker to the worker thread
        self.worker.moveToThread(self.worker_thread)

        # start the thread
        self.worker_thread.start()
        #################################

        ########### TERMAL WORKER ############
        self.termal_worker = Worker()
        self.termal_worker_thread = QThread()

        self.termal_worker.progress.connect(self.update_termal_status)

        self.termal_work_requested.connect(self.termal_worker.do_work)

        self.termal_worker.completed.connect(self.complete)

        # move worker to the worker thread
        self.termal_worker.moveToThread(self.termal_worker_thread)

        # start the thread
        self.termal_worker_thread.start()
        #######################################

        start_button = QPushButton("СТАРТ", clicked=self.start_button_clicked)
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

    is_xeryon_exist = False
    is_termal_exist = False
    is_Rigol_exist = False
    is_Vega_exist = False


    def complete(self, v):
        self.start_button.setEnabled(True)


    def init_Xeryon(self, device_name):
        if Path(device_name).exists():
            self.controller = Xeryon(device_name, 115200)
            self.axisX = self.controller.addAxis(Stage.XRTU_30_109, "X")
            self.controller.start()
            self.axisX.findIndex()
            self.axisX.setUnits(Units.deg)
            self.is_xeryon_exist = True
            self.Xeryon_cbox.setChecked(True)

    def init_Vega(self, device_name):
        if Path(device_name).exists():
            self.is_Vega_exist = True
            self.vega = Ophir.VegaPowerMeter(device_name, 9600)

    def init_Rigol(self):
        if glob('/dev/usbtmc*'):
            self.is_Rigol_exist = True
            self.Rigol_cbox.setChecked(True)
            self.osc = rigol2000a.Rigol2072a()
            # Change voltage range of channel 1 to 50mV/div.
            self.osc[2].set_vertical_scale_V(0.02)

    def init_termal(self, device_name):
        if Path(device_name).exists():
            self.Termal_cbox.setChecked(True)

            SERIALPORT = device_name
            BAUDRATE = 115200
            ser = serial.Serial(SERIALPORT, BAUDRATE)
            ser.bytesize = serial.EIGHTBITS  # number of bits per bytes
            ser.parity = serial.PARITY_EVEN  # set parity check: no parity
            ser.stopbits = serial.STOPBITS_ONE  # number of stop bits
            ser.timeout = 2  # timeout block read
            ser.writeTimeout = 0  # timeout for writereturn ser
            self.is_termal_exist = True
            
            return ser


################### --Integral-- #######################
    x_value = []
    y_value = []

    def intergal_per_area(self):
        # self.osc[2].get_data('norm', 'channel%i.dat' % 2)
        self.get_data_for_integral("channel2.dat")

        summ = 0
        for indx in range(len(self.x_value) - 1):
            half = (self.x_value[indx + 1] -
                    self.x_value[indx]) / 2

            step = self.y_value[indx] + self.y_value[indx + 1]
            summ += half * step
        if summ < 0:
            summ *= -1

        self.graphWidget.plot(self.x_value, self.y_value)
        print("res: ")
        print(summ)
        return summ

    def get_data_for_integral(self, filemane):
        file1 = open(filemane, 'r')
        Lines = file1.readlines()
        for line in Lines:
            if float(''.join(re.findall("[^,]*,(.*)", line))) < float(0.025) and float(''.join(re.findall("^(.+?),", line))) > float(4e-08):
                # value before comma exept comma
                self.x_value.append(
                    float(''.join(re.findall("^(.+?),", line))))
                # value after comma except comma
                self.y_value.append(
                    float(''.join(re.findall("[^,]*,(.*)", line))))

##############################

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

    def set_ang_button_clicked(self):
        if self.is_xeryon_exist:
            self.axisX.setDPOS(self.set_ang_line_edit.text())
            if (self.device_choice.currentText() == "RIGOL Oscilloscope"):
                self.label_cur_vcc.setText(
                    "Интенсивность: " + str(round((float(self.osc[2].get_vpp()) * float(1000)), 2)) + " у:е")
            else:
                time.sleep(3)
                self.label_cur_vcc.setText(
                    "Мощность: " + str(round((float(self.vega.get_power()) * float(1000)), 2)) + " мВт")

    # def binary_search(self, arr, low, high, x):
    #     if high >= low:
    #         mid = (high + low) // 2
    #         if round(float(arr[mid]), 2) == round(x, 2):
    #             return mid
    #         elif round(float(arr[mid]), 2) > round(x, 2):
    #             return self.binary_search(arr, low, mid - 1, x)
    #         else:
    #             return self.binary_search(arr, mid + 1, high, x)
    #     else:
    #         return -1

    def start_button_clicked(self):
        if self.is_xeryon_exist:
            if re.findall("\d+\.\d+", str(self.start_line_edit.text())) == "" or re.findall("\d+\.\d+", str(self.stop_line_edit.text())) == "":
                self.label_status.setText("Введите число в фромате dddd.dddd")
                time.sleep(1)
            else:
                self.cur_ang = round(float(self.start_line_edit.text()), 2)
                self.angles_indx = 0
                while round(float(self.cur_ang), 2) != round(float(self.angles[self.angles_indx]), 2):
                    if round(float(self.cur_ang), 2) > round(float(self.angles[self.angles_indx]), 2):
                        self.cur_ang -= 0.05
                    elif self.angles_indx < len(self.angles):
                        self.angles_indx += 1

                self.axisX.setDPOS(float(self.cur_ang))

                # self.timer.start()
                self.wave_indx = 0
                self.x.clear()
                self.y.clear()
                self.stop_plot = 1
                print(self.stop_plot)
                self.stop_do_it = 0
                self.work_requested.emit(2)
                self.worker.is_working = True

    def stop_button_clicked(self):
        # self.intergal_per_area()
        if self.is_xeryon_exist:
            self.axisX.reset()
            self.controller.stop()

        self.worker.is_working = False
        self.termal_worker.is_working = False

    cur_ang = 0
    wave_indx = 0
    angles_indx = 0
    angles = []
    wave_numbers = []
    x = []
    y = []
    stop_plot = 0

    i = 0

    def update_plot(self):
        if self.stop_plot != 0:
            # print("cur_ang ", self.cur_ang)
            self.axisX.setDPOS(self.angles[self.angles_indx])
            #
            time.sleep(0.1)
            #   Rigol or Vega
            self.x.append(float(self.wave_numbers[self.wave_indx]))

            if (self.device_choice.currentText() == "RIGOL Oscilloscope") and self.is_Rigol_exist:
                # self.intergal_per_area()
                self.y.append(float(self.osc[2].get_vpp()) * float(1000))
            elif self.is_Vega_exist:
                time.sleep(3)
                self.y.append(float(self.vega.get_power()) * float(1000))

            self.data_line.setData(self.x, self.y)

            self.wave_indx += 1
            self.angles_indx += 1

            if round(float(self.cur_ang), 2) < round(float(self.stop_line_edit.text()), 2):
                self.stop_plot = 0
                self.worker.is_working = False

# ---------Termal-------------
    termal_enable_status = 0

    def termal_on_button_clicked(self):
        # self.termal_work_requested.emit(10)
        self.termal_send_command("enable")
        self.termal_enable_status = 1

    def termal_off_button_clicked(self):
        self.termal_send_command("disable")
        self.termal_enable_status = 0

    def update_termal_status(self):
        self.termal_send_command("gist")
        # self.termal_send_command("ps")

    def termal_send_command(self, command):
        if self.is_termal_exist:
            str_temp = ""
            current_temp = ""

            if not self.ser.isOpen():
                self.ser.open()

            if self.ser.isOpen():
                try:
                    self.ser.flushInput()  # flush input buffer, discarding all its contents
                    self.ser.flushOutput()  # flush output buffer, aborting current output
                    command += '\r'
                    self.ser.write(command.encode('ascii'))
                    time.sleep(0.5)
                    while True:
                        response = self.ser.readline().decode('utf-8', errors='ignore')
                        print("----read data: " + response)
                        if response == '':
                            print("finish reading")
                            break

                        if command == 'gist':
                            current_temp = re.findall("\d+\.\d+", response)
                            break

                        if response == '01':
                            str_temp = "01 ERROR"
                            break

                    self.ser.close()
                except Exception as e:
                    print("error communicating...: " + str(e))
            else:
                print("cannot open serial port ")

            if str_temp != "01 ERROR":
                str_temp = "Температура лазера= " + \
                    ''.join(current_temp) + " С || " + \
                    "Установленная температура лазера = 18 C "
                if self.termal_enable_status == 1:
                    str_temp += "|| Охлаждение Включено"
                else:
                    str_temp += "|| Охлаждение Выключено"

            self.label_status.setText(str_temp)


########################
app = QtWidgets.QApplication(sys.argv)
w = MainWindow()
w.show()
sys.exit(app.exec_())
