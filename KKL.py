from Xeryon import *
# from pylablib.devices import Ophir
import rigol2000a

import serial
import time

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QMessageBox, QPushButton, QVBoxLayout,  QCheckBox, QHBoxLayout, QLabel, QFrame, QLineEdit, QComboBox
from PyQt5 import QtWidgets, QtCore

from PyQt5.QtGui import QFont, QIcon

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

import numpy as np


class Xeryon_Worker():

    is_Xeryon_exist = False

    def init_Xeryon(self, device_name):
        if Path(device_name).exists():
            self.controller = Xeryon(device_name, 115200)
            self.axisX = self.controller.addAxis(Stage.XRTU_30_109, "X")
            self.controller.start()
            self.axisX.findIndex()
            self.axisX.setUnits(Units.deg)
            self.is_Xeryon_exist = True


class Rigol_Worker(QObject, Xeryon_Worker):
    sent_avarage_integral_value = Signal(float, float)

    sent_intergal_value = Signal(float)

    is_working = False
    is_Rigol_exist = False

    angles_indx = 0
    wave_indx = 0
    wave_indx = 0

    def __del__(self):
        if self.is_Xeryon_exist:
            self.axisX.reset()
            self.controller.stop()

    def __init__(self):
        super(Rigol_Worker, self).__init__()

        self.init_Rigol()
        self.init_Xeryon("/dev/ttyACM0")

        self.angles = self.from_file_to_list("angles.txt")
        self.wave_numbers = self.from_file_to_list("wave_numbers.txt")

    def init_Rigol(self):
        if glob('/dev/usbtmc*'):
            self.osc = rigol2000a.Rigol2072a()
            # Change voltage range of channel 1 to 50mV/div.
            self.osc[1].set_vertical_scale_V(0.05)
            self.osc[2].set_vertical_scale_V(0.05)
            self.is_Rigol_exist = True

    def get_start_angle_value(self, value):
        self.curent_ang = round(float(value), 2)

        self.angles_indx = 0
        self.wave_indx = 0
        while round(float(self.curent_ang), 2) != round(float(self.angles[self.angles_indx]), 2):
            if round(float(self.curent_ang), 2) > round(float(self.angles[self.angles_indx]), 2):
                self.curent_ang -= 0.05
            elif self.angles_indx < len(self.angles):
                self.angles_indx += 1
                self.wave_indx += 1

        self.axisX.setDPOS(float(self.curent_ang))

    def from_file_to_list(self, filemane):
        list = []
        file1 = open(filemane, 'r')
        Lines = file1.readlines()

        for line in Lines:
            list.append(line)

        return list

    ################### --Integral-- #######################
    calc_error = False
    ch1_x = []
    ch1_y = []
    ch2_x = []
    ch2_y = []

    def intergal_per_area(self):
        self.calc_error = False
        self.osc[1].get_data('norm', 'channel%i.dat' % 1)
        self.osc[2].get_data('norm', 'channel%i.dat' % 2)

        filename = "channel" + "1" + ".dat"
        self.get_data_for_integral(filename, 1, self.ch1_x, self.ch1_y)
        filename = "channel" + "2" + ".dat"
        self.get_data_for_integral(filename, 2, self.ch2_x, self.ch2_y)

        self.move_integral_data(self.ch1_y)
        self.move_integral_data(self.ch2_y)

        result = 0
        if self.calc_error:
            print("error")
        else:
            # ch1_sum = np.trapz(self.ch1_y, self.ch1_x)
            # ch2_sum = np.trapz(self.ch2_y, self.ch2_x)
            ch1_sum = self.calculate_trapezoidal_sum(self.ch1_x, self.ch1_y)
            ch2_sum = self.calculate_trapezoidal_sum(self.ch2_x, self.ch2_y)

            if float(ch2_sum) != 0:
                result = float(ch1_sum) / float(ch2_sum)
            else:
                print("<< devision by zero >>")
                self.calc_error = True

        return result

    def move_integral_data(self, y_array):
        if np.any(y_array):
            max_value = max(y_array)
            for item in y_array:
                item = item - max_value
                item *= -1
        else:
            print("<< recive empty data from channel >>")
            self.calc_error = True

    def calculate_trapezoidal_sum(self, x_array, y_array):
        summ = 0
        for indx in range(len(x_array) - 1):

            half = (abs(y_array[indx]) + abs(y_array[indx + 1])) / 2

            step = (x_array[indx + 1] -
                    x_array[indx])

            summ += half * step

        return summ

    def get_data_for_integral(self, filemane, chan_num, x_array, y_array):
        x_array.clear()
        y_array.clear()

        file1 = open(filemane, 'r')
        Lines = file1.readlines()

        counter = 1

        for line in Lines:
            # value before comma exept comma
            x = float(''.join(re.findall("^(.+?),", line)))
            # value after comma except comma
            y = float(''.join(re.findall("[^,]*,(.*)", line)))

            if chan_num == 1:
                if float(x) > float(3.2e-07) and float(x) < float(1.14e-06) and float(y) < float(0.05):
                    x_array.append(float(x))
                    y_array.append(float(y))
                    counter += 1
            elif chan_num == 2:
                if float(x) > float(1.02e-06) and float(x) < float(1.87e-06) and float(y) < float(0.05):
                    x_array.append(float(x))
                    y_array.append(float(y))
                    counter += 1

##############################

    def avarage_integral_calc(self):
        res = 0
        avarage_counter = 0
        start = time.time()
        if self.is_Rigol_exist:
            for i in range(0, 10):
                integral = float(self.intergal_per_area())
                print(integral)
                avarage_counter += 1
                if integral > 0.5 and integral < 6:
                    res += float(integral)
            res = float(res) / avarage_counter

        print("res: " + str(res))
        end = time.time()
        print("Calc time = " + str(end - start))

        return float(res)

    def move_motor(self, value):
        if self.is_Rigol_exist and self.is_Xeryon_exist:
            self.axisX.setDPOS(value)
            self.sent_intergal_value.emit(
                round(self.avarage_integral_calc(), 2))

    def step_motor(self):
        if self.is_Rigol_exist:
            self.axisX.setDPOS(self.angles[self.angles_indx])
            print(self.angles[self.angles_indx])
            self.angles_indx += 1
            self.wave_indx += 1

    @Slot()
    def do_work(self):
        self.is_working = True
        while self.is_working:
            time.sleep(0.1)
            self.step_motor()
            self.sent_avarage_integral_value.emit(
                self.avarage_integral_calc(), int(self.wave_numbers[self.wave_indx]))


class Termal_Worker(QObject):
    sent_current_temperature_value = Signal(float)

    is_working = False

    is_Termal_exist = False

    is_Termal_turn_On = False

    def __init__(self):
        super(Termal_Worker, self).__init__()

        self.ser = self.init_termal("/dev/ttyUSB0")

    def init_termal(self, device_name):
        if Path(device_name).exists():
            SERIALPORT = device_name
            BAUDRATE = 115200
            ser = serial.Serial(SERIALPORT, BAUDRATE)
            ser.bytesize = serial.EIGHTBITS
            ser.parity = serial.PARITY_EVEN
            ser.stopbits = serial.STOPBITS_ONE
            ser.timeout = 2
            ser.writeTimeout = 0
            self.is_Termal_exist = True

            return ser

    def termal_turn_on(self):
        self.termal_send_command("enable")

    def termal_turn_off(self):
        self.termal_send_command("disable")

    def update_termal_status(self):
        self.termal_send_command("gist")

    def termal_send_command(self, command):
        if self.is_Termal_exist:
            if not self.ser.isOpen():
                self.ser.open()

            if self.ser.isOpen():
                try:
                    self.ser.flushInput()  # flush input buffer, discarding all its contents
                    self.ser.flushOutput()  # flush output buffer, aborting current output
                    command += '\r'
                    self.ser.write(command.encode('ascii'))
                    time.sleep(0.2)
                    while True:
                        response = self.ser.readline().decode('utf-8', errors='ignore')
                        print("----read data: " + response)
                        if response == '':
                            print("finish reading")
                            break

                        if command == "gist" + '\r':
                            self.sent_current_temperature_value.emit(
                                round(float(''.join(re.findall("\d+\.\d+", response))), 2))
                            break

                        if command == "enable" + '\r' and response == '00':
                            self.is_Termal_turn_On = True

                        if command == "disable" + '\r' and response == '00':
                            self.is_Termal_turn_On = False

                        if response == '01':
                            print("01 ERROR !!!")
                            break

                    self.ser.close()

                except Exception as e:
                    print("error communicating...: " + str(e))
            else:
                print("cannot open serial port ")

    @Slot()
    def do_work(self):
        self.is_working = True
        while self.is_working:
            time.sleep(10)
            self.update_termal_status()


class MainWindow(QtWidgets.QMainWindow):
    move_Xeryon = Signal(str)

    start_rigol_xeryon_work = Signal()

    sent_start_xeryon_angle = Signal(float)

    termal_start_work = Signal()

    turn_on_termal = Signal()
    turn_off_termal = Signal()

    #########
    x = []
    y = []
    ###########
    color_array = ['green', 'orange', 'darkRed', 'darkCyan',
                   'yellow', 'darkMagenta', 'blue', 'red', 'cyan', 'magenta', 'black']

    color_index = -1

    def closeEvent(self, event):
        self.close_window(event)

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.init_widgets()

        ################  RIGOL WORKER  #################
        self.rigol = Rigol_Worker()
        self.rigol_thread = QThread()

        self.move_Xeryon.connect(self.rigol.move_motor)

        self.rigol.sent_intergal_value.connect(
            self.print_intergal_value)

        self.start_rigol_xeryon_work.connect(self.rigol.do_work)

        self.sent_start_xeryon_angle.connect(self.rigol.get_start_angle_value)

        self.rigol.sent_avarage_integral_value.connect(self.update_plot)

        self.rigol.moveToThread(self.rigol_thread)

        ########### TERMAL WORKER ############
        self.termal = Termal_Worker()
        self.termal_thread = QThread()

        self.turn_on_termal.connect(self.termal.termal_turn_on)

        self.turn_off_termal.connect(self.termal.termal_turn_off)

        self.termal.sent_current_temperature_value.connect(
            self.print_current_temperature)

        self.termal_start_work.connect(self.termal.do_work)

        # move worker to the worker thread
        self.termal.moveToThread(self.termal_thread)

        # start the thread
        self.termal_thread.start()
        ############## INIT DEVICES ################
        self.init_Xeryon("/dev/ttyACM0")
        self.init_Rigol()
        self.init_termal()

        self.termal_on_button_clicked()

    def init_Xeryon(self, device_name):
        if Path(device_name).exists():
            self.Xeryon_cbox.setChecked(True)

    def init_Rigol(self):
        if self.rigol.is_Rigol_exist:
            self.Rigol_cbox.setChecked(True)

    def init_termal(self):
        if self.termal.is_Termal_exist:
            self.Termal_cbox.setChecked(True)

    def set_ang_button_clicked(self):
        self.move_Xeryon.emit(self.set_ang_line_edit.text())

    def print_intergal_value(self, value):
        self.label_integral_value.setText(str(value))

    def start_button_clicked(self):
        if self.rigol.is_Xeryon_exist:
            if re.findall("\d+\.\d+", str(self.start_line_edit.text())) == "" or re.findall("\d+\.\d+", str(self.stop_line_edit.text())) == "":
                self.label_status.setText("Введите число в фромате dddd.dddd")
                time.sleep(0.1)
            else:
                self.x.clear()
                self.y.clear()

                if self.several_plots_enable_cbox.isChecked():
                    if self.color_index < (len(self.color_array) - 1):
                        self.color_index += 1
                    else:
                        self.color_index = 0
                    print("color index : " + str(self.color_index))
                else:
                    self.color_index = 0
                    self.graphWidget.clear()

                self.rigol_thread.start()
                self.sent_start_xeryon_angle.emit(
                    round(float(self.start_line_edit.text()), 2))
                self.start_rigol_xeryon_work.emit()
                self.start_button.setEnabled(False)

    def stop_button_clicked(self):
        self.rigol.is_working = False
        self.rigol_thread.wait(5000)
        self.start_button.setEnabled(True)

    def save_data_to_file(self):
        filename = "user_spectr_" + \
            time.strftime("%H:%M:%S-%d.%m.%Y") + \
            '_' + str(self.color_array[self.color_index]) + ".txt"
        file = open(filename, "w+")
        for index in range(len(self.x)):
            st = str(float(self.x[index])) + \
                " " + str(float(self.y[index])) + "\n"
            file.write(st)
        file.close()

    def update_plot(self, avarage_integral, wave_number):
        self.x.append(float(wave_number))
        self.y.append(float(avarage_integral))

        if self.several_plots_enable_cbox.isChecked():
            pen = pg.mkPen(color=self.color_array[self.color_index], width=8,
                           style=QtCore.Qt.SolidLine)
            self.graphWidget.plot(self.x, self.y, pen=pen)
        else:
            pen = pg.mkPen(color=(0, 255, 0), width=8,
                           style=QtCore.Qt.SolidLine)
            self.data_line = self.graphWidget.plot(
                self.x, self.y, name="my plot",  pen=pen)
            self.data_line.setData(self.x, self.y)

    def clear_plot(self):
        self.graphWidget.clear()


###############  Termal ########


    def termal_on_button_clicked(self):
        self.turn_on_termal.emit()
        self.termal_start_work.emit()

    def termal_off_button_clicked(self):
        self.turn_off_termal.emit()

    def print_current_temperature(self, current_temp):
        str_temp = "Температура лазера= " + \
            str(current_temp) + " С || " + \
            "Установленная температура лазера = 18 C "

        if self.termal.is_Termal_turn_On:
            str_temp += "|| Охлаждение Включено"
        else:
            str_temp += "|| Охлаждение Выключено"

        self.label_status.setText(str_temp)
###########################

    def init_widgets(self):
        # self.setWindowIcon(
        #     QtGui.QIcon('KKL.png'))
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

        ##############
        self.start_button = QPushButton(
            "СТАРТ", clicked=self.start_button_clicked)

        self.stop_button = QPushButton(
            "СТОП",  clicked=self.stop_button_clicked)

        self.label_status = QLabel("")
        self.label_status.setFrameStyle(QFrame.Panel | QFrame.Sunken)

        layout = QVBoxLayout()
        layout.addLayout(device_list_layout)
        layout.addWidget(self.graphWidget)

        # NEW
        new_layout = QHBoxLayout()

        self.clear_plot_button = QPushButton(
            "Очистить график",  clicked=self.clear_plot)
        self.several_plots_enable_cbox = QCheckBox(
            "Отображать прошлые спектры")
        new_layout.addWidget(self.several_plots_enable_cbox)
        new_layout.addWidget(self.clear_plot_button)
        layout.addLayout(new_layout)

        # START
        start_layout = QHBoxLayout()
        self.start_label = QLabel("Начальный угол: ")
        self.start_line_edit = QLineEdit("110")
        termal_on_button = QPushButton("ВКЛ. ОХЛАЖДЕНИЕ")
        termal_on_button.clicked.connect(self.termal_on_button_clicked)
        start_layout.addWidget(self.start_label)
        start_layout.addWidget(self.start_line_edit)
        start_layout.addWidget(self.start_button)
        start_layout.addWidget(termal_on_button)
        layout.addLayout(start_layout)

        # STOP
        stop_layout = QHBoxLayout()
        self.stop_label = QLabel("Конечный угол: ")
        self.stop_line_edit = QLineEdit("93.75")
        termal_off_button = QPushButton("ВЫКЛ. ОХЛАЖДЕНИЕ")
        termal_off_button.clicked.connect(self.termal_off_button_clicked)
        stop_layout.addWidget(self.stop_label)
        stop_layout.addWidget(self.stop_line_edit)
        stop_layout.addWidget(self.stop_button)
        stop_layout.addWidget(termal_off_button)
        layout.addLayout(stop_layout)

        # Set angle
        set_ang_layout = QHBoxLayout()

        set_ang_button = QPushButton("Установить угол")
        set_ang_button.clicked.connect(self.set_ang_button_clicked)
        save_to_file_button = QPushButton(
            "Сохранить данные последнего спектра в файл")
        save_to_file_button.clicked.connect(self.save_data_to_file)
        self.set_ang_line_edit = QLineEdit("101.1")
        self.set_ang_label = QLabel("Интенсивность:")
        self.label_integral_value = QLabel("")
        self.set_ang_label_ye = QLabel("у:е")
        self.label_integral_value.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        set_ang_layout.addWidget(set_ang_button)
        set_ang_layout.addWidget(self.set_ang_line_edit)
        set_ang_layout.addWidget(self.set_ang_label)
        set_ang_layout.addWidget(self.label_integral_value)
        set_ang_layout.addWidget(self.set_ang_label_ye)
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

    def close_window(self, event):

        ret = QtWidgets.QMessageBox.warning(None, 'Внимание!', 'Лазер Выключен?',
                                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                            QtWidgets.QMessageBox.Yes)
        if ret == QtWidgets.QMessageBox.Yes:
            self.turn_off_termal.emit()
            time.sleep(0.2)
            QtWidgets.QMainWindow.closeEvent(self, event)
        else:
            QtWidgets.QMainWindow.closeEvent(self, event)
            # event.ignore()

        self.termal.is_working = False
        self.rigol.is_working = False
        self.rigol_thread.wait(1000)
        self.termal_thread.wait(1000)


########################
app = QtWidgets.QApplication(sys.argv)
w = MainWindow()
w.show()
sys.exit(app.exec_())
