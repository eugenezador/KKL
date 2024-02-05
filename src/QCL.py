
from copy import deepcopy
import json
from Xeryon import *
# from pylablib.devices import Ophir
import rigol2000a

import serial
import time

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QMessageBox, QPushButton, QVBoxLayout,  QCheckBox, QHBoxLayout, QLabel, QFrame, QLineEdit, QComboBox, QPlainTextEdit, QProgressBar
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

import os.path


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
    sent_avarage_integral_value = Signal(float, float, float)

    sent_intergal_value = Signal(float, float)

    sent_logging_info = Signal(str)

    finish_spectrum_plotting = Signal()

    increase_step_progress_bar = Signal(int)
    increase_spectrum_progress_bar = Signal(float)

    reset_progress_bar = Signal()

    is_working = False
    is_Rigol_exist = False

    stop_angle = 0.0

    angles_indx = 0
    wave_indx = 0

    progress_steps_amount = 0
    persent_progress = 0
    progress_step = 0

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

    def get_start_stop_angle_value(self, start_angle, stop_angle):
        self.current_angle = round(float(start_angle), 2)
        self.stop_angle = round(float(stop_angle), 2)
        self.angles_indx = 0
        self.wave_indx = 0
        self.filter_start_angle()
        # while round(float(self.current_angle), 2) != round(float(self.angles[self.angles_indx]), 2):
        #     if round(float(self.current_angle), 2) > round(float(self.angles[self.angles_indx]), 2):
        #         self.current_angle -= 0.05
        #     elif self.angles_indx < len(self.angles):
        #         self.angles_indx += 1
        #         self.wave_indx += 1

        self.progress_steps_amount = self.binary_search(
            self.angles, self.stop_angle) - self.binary_search(self.angles, self.current_angle)
        self.progress_step = 100 / self.progress_steps_amount

        self.axisX.setDPOS(float(self.current_angle))

    def filter_start_angle(self):
        if round(float(self.current_angle), 2) > round(float(self.angles[0]), 2):
            self.current_angle == round(float(self.angles[0]), 2)
        else:
            while round(float(self.current_angle), 2) != round(float(self.angles[self.angles_indx]), 2):
                if round(float(self.current_angle), 2) < round(float(self.angles[self.angles_indx]), 2):
                    self.current_angle += 0.05
        self.wave_indx = self.binary_search(self.angles, self.current_angle)
        self.angles_indx = self.binary_search(self.angles, self.current_angle)

        

    def from_file_to_list(self, filemane):
        list = []
        file1 = open(filemane, 'r')
        Lines = file1.readlines()

        for line in Lines:
            list.append(line)

        return list

    def binary_search(self, list, value):
        first = 0
        last = len(list)-1
        while (first <= last):
            mid = (first+last)//2
            if round(float(list[mid]), 2) == round(float(value), 2):
                return mid
            elif round(float(list[mid]), 2) > round(float(value),2):
                first = mid+1
            else:
                last = mid-1
        return -1

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
        # avarage_counter = 0
        # start = time.time()
        if self.is_Rigol_exist:
            for avarage_counter in range(0, 10):
                integral = float(self.intergal_per_area())
                self.sent_logging_info.emit(str(integral))
                self.increase_step_progress_bar.emit(avarage_counter * 10)
                # print(integral)
                avarage_counter += 1
                if integral > 0.5 and integral < 6:
                    res += float(integral)
            res = float(res) / avarage_counter

        # print("intensty: " + str(res))
        self.sent_logging_info.emit("intensty: " + str(res))
        # end = time.time()
        # print("Calc time = " + str(end - start))

        return float(res)

    def move_motor(self, value):
        if self.is_Rigol_exist and self.is_Xeryon_exist:
            self.axisX.setDPOS(value)
            self.sent_logging_info.emit(
                "current angle: " + str(value))
            self.sent_intergal_value.emit(
                round(float(value), 2), round(self.avarage_integral_calc(), 2))

    def step_motor(self):
        if self.is_Rigol_exist and self.is_Xeryon_exist:
            self.axisX.setDPOS(self.angles[self.angles_indx])
            # print(self.angles[self.angles_indx])
            self.current_angle = self.angles[self.angles_indx]
            self.sent_logging_info.emit(
                "current angle: " + self.angles[self.angles_indx])
            self.angles_indx += 1
            self.wave_indx += 1

    @Slot()
    def do_work(self):
        self.is_working = True
        while self.is_working:
            if round(float(self.current_angle), 2) <= round(float(self.stop_angle), 2):
                self.is_working = False
                break
            time.sleep(0.1)
            self.step_motor()
            self.sent_avarage_integral_value.emit(round(float(self.current_angle), 2), int(
                self.wave_numbers[self.wave_indx]), self.avarage_integral_calc())

            if round(float(self.current_angle), 2) == round(float(self.stop_angle), 2):
                self.increase_spectrum_progress_bar.emit(100)

            self.increase_spectrum_progress_bar.emit(
                np.floor(self.persent_progress))
            print(self.persent_progress)
            self.persent_progress += self.progress_step
            self.reset_progress_bar.emit()

        self.finish_spectrum_plotting.emit()


class Termal_Worker(QObject):
    sent_current_temperature_value = Signal(float)

    sent_logging_info = Signal(str)

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
                        self.sent_logging_info.emit(
                            "read termal data: " + response)
                        # print("----read data: " + response)
                        if response == '':
                            # print("finish reading")
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
                            self.sent_logging_info.emit("Termal 01 ERROR !!!")
                            # print("01 ERROR !!!")
                            break

                    self.ser.close()

                except Exception as e:
                    self.sent_logging_info.emit(
                        "error communicating...: " + str(e))
                    # print("error communicating...: " + str(e))
            else:
                self.sent_logging_info.emit("cannot open serial port !")

    @Slot()
    def do_work(self):
        self.is_working = True
        while self.is_working:
            time.sleep(10)
            self.update_termal_status()


class MainWindow(QtWidgets.QMainWindow):
    move_Xeryon = Signal(str)

    start_rigol_xeryon_work = Signal()

    sent_start_xeryon_angle = Signal(float, float)

    termal_start_work = Signal()

    turn_on_termal = Signal()
    turn_off_termal = Signal()

    #########
    saved_spectrums_map = dict()

    current_termal_temperature = 0
    start_time = 0
    stop_time = 0

    #########
    angle = []
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
        self.init_Rigol_Worker()

        ########### TERMAL WORKER ############
        self.init_Termal_Worker()

        ############## INIT DEVICES ################
        self.init_Xeryon("/dev/ttyACM0")
        self.init_Rigol()
        self.init_termal()
        self.Xeryon_cbox.setEnabled(False)
        self.Rigol_cbox.setEnabled(False)
        self.Termal_cbox.setEnabled(False)

        self.termal_button_clicked()

    def init_Rigol_Worker(self):
        self.rigol = Rigol_Worker()
        self.rigol_thread = QThread()

        self.move_Xeryon.connect(self.rigol.move_motor)

        self.rigol.sent_intergal_value.connect(
            self.print_intergal_value)

        self.start_rigol_xeryon_work.connect(self.rigol.do_work)

        self.rigol.increase_step_progress_bar.connect(
            self.update_step_progress_bar)
        self.rigol.increase_spectrum_progress_bar.connect(
            self.update_spectrum_progress_bar)

        self.rigol.reset_progress_bar.connect(self.step_progress_bar.reset)

        self.sent_start_xeryon_angle.connect(
            self.rigol.get_start_stop_angle_value)
        self.rigol.finish_spectrum_plotting.connect(self.stop_button_clicked)

        self.rigol.sent_avarage_integral_value.connect(self.update_plot)
        self.rigol.sent_logging_info.connect(self.print_logging_info)

        self.rigol.moveToThread(self.rigol_thread)

    def init_Termal_Worker(self):
        self.termal = Termal_Worker()
        self.termal_thread = QThread()

        self.turn_on_termal.connect(self.termal.termal_turn_on)

        self.turn_off_termal.connect(self.termal.termal_turn_off)
        self.termal.sent_logging_info.connect(self.print_logging_info)

        self.termal.sent_current_temperature_value.connect(
            self.print_current_temperature)

        self.termal_start_work.connect(self.termal.do_work)

        # move worker to the worker thread
        self.termal.moveToThread(self.termal_thread)

        # start the thread
        self.termal_thread.start()

    def update_step_progress_bar(self, value):
        if value <= self.step_progress_bar.maximum():
            self.step_progress_bar.setValue(value)
            self.step_progress_bar.setFormat(
                "Запись шага: " + str(value) + '%')

    def update_spectrum_progress_bar(self, value):
        if value <= self.spectrum_progress_bar.maximum():
            self.spectrum_progress_bar.setValue(int(value))
            self.spectrum_progress_bar.setFormat(
                "Запись спектра: " + str(value) + '%')

    def print_logging_info(self, log_str):
        self.logging.appendPlainText(log_str)

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
        # self.logging.clear()
        self.move_Xeryon.emit(self.set_ang_line_edit.text())

    def print_intergal_value(self, intensity):
        self.intensity_value.setText(str(intensity))

    def start_button_clicked(self):
        if self.rigol.is_Xeryon_exist:
            if re.findall("\d+\.\d+", str(self.start_line_edit.text())) == "" or re.findall("\d+\.\d+", str(self.stop_line_edit.text())) == "":
                self.label_status.setText("Введите число в фромате dddd.dddd")
                time.sleep(0.1)
            else:
                self.angle.clear()
                self.is_new_tick_scale = True
                self.x.clear()
                self.y.clear()
                self.spectrum_progress_bar.reset()
                self.rigol.persent_progress = 0

                if self.several_plots_enable_cbox.isChecked():
                    if self.color_index < (len(self.color_array) - 1):
                        self.color_index += 1
                    else:
                        self.color_index = -1
                else:
                    self.color_index = 0
                    self.graphWidget.clear()
                    self.saved_spectrums_map.clear()

                self.start_time = time.strftime("%H:%M:%S-%d.%m.%Y")
                self.rigol_thread.start()
                self.sent_start_xeryon_angle.emit(
                    round(float(self.start_line_edit.text()), 2), round(float(self.stop_line_edit.text()), 2))
                self.start_rigol_xeryon_work.emit()
                self.start_button.setEnabled(False)

    def stop_button_clicked(self):
        self.rigol.is_working = False
        self.rigol_thread.wait(5000)
        self.start_button.setEnabled(True)
        if self.angle or self.x or self.y:
            self.saved_spectrums_map[self.color_index] = []
            self.saved_spectrums_map[self.color_index].append(
                deepcopy(self.angle))
            self.saved_spectrums_map[self.color_index].append(deepcopy(self.x))
            self.saved_spectrums_map[self.color_index].append(deepcopy(self.y))
            self.saved_spectrums_map[self.color_index].append(
                deepcopy(self.start_time))
            self.saved_spectrums_map[self.color_index].append(
                deepcopy(time.strftime("%H:%M:%S-%d.%m.%Y")))

    def save_data_to_file(self):
        os.makedirs("../result", exist_ok=True)
        for key, value in self.saved_spectrums_map.items():

            filename = "user_spectr_" + \
                time.strftime("%H:%M:%S-%d.%m.%Y") + \
                '_' + str(self.color_array[key]) + ".json"
            with open(os.path.join("../result", filename), "w+") as f:
                jsonfile_data = []
                jsonfile_data.append({
                    "Laser chip temperature": self.current_termal_temperature,
                    "Pressure inside laser cell: ": "",
                    "Ambient temperature: ": "",
                    "Humidity: ": "",
                    "Environmental pressure": "",
                    "Start time: ": value[3],
                    "Stop time: ": value[4]
                })
                jsonfile_data.append({
                    "plot_color": self.color_array[key],
                    "angles": value[0],
                    "wave_numbers": value[1],
                    "intensity": value[2]
                })
                json.dump(jsonfile_data, f, indent=4)
                f.close()

    # def save_data_to_file(self):
    #     os.makedirs("../result", exist_ok=True)
    #     for key, value in self.saved_spectrums_map.items():
    #         filename = "user_spectr_" + \
    #             time.strftime("%H:%M:%S-%d.%m.%Y") + '_' + \
    #             str(self.color_array[key]) + ".txt"
    #         with open(os.path.join("../result", filename), "w+") as f:
    #             st = "Angle" + \
    #                 "\t" + "Wave_number" + "\t" + "Intensity" + "\n"
    #             f.write(st)
    #             for i in range(len(value[0])):
    #                 st = str(float(value[0][i])) + \
    #                     "\t" + str(float(value[1][i])) + \
    #                     "\t" + '\t' + str(float(value[2][i])) + "\n"
    #                 print(st)
    #                 f.write(st)
    #             f.close()

    is_new_tick_scale = True

    def update_plot(self, angle, wave_number, avarage_integral):
        self.angle.append(angle)
        self.x.append(float(wave_number))
        self.y.append(float(avarage_integral))
        print(float(avarage_integral))

        if len(self.x) > 2 and self.is_new_tick_scale:
            self.graphWidget.getAxis("bottom").setTickSpacing(
                levels=[(22, 0)])
            self.graphWidget.getAxis("left").setTickSpacing(
                levels=[(0.1, 0)])
            self.is_new_tick_scale = False

        if self.several_plots_enable_cbox.isChecked():
            pen = pg.mkPen(color=self.color_array[self.color_index], width=6,
                           style=QtCore.Qt.SolidLine)
            self.graphWidget.plot(self.x, self.y, pen=pen)
        else:
            # self.color_index = 0
            pen = pg.mkPen(color=self.color_array[self.color_index], width=6,
                           style=QtCore.Qt.SolidLine)
            self.data_line = self.graphWidget.plot(
                self.x, self.y, name="my plot",  pen=pen)
            self.data_line.setData(self.x, self.y)

    def clear_plot(self):
        self.graphWidget.clear()
        self.saved_spectrums_map.clear()
        self.color_index = -1

    # def clear_logging(self):
    #     self.logging.clear()


###############  Termal ########

    is_termal_on = False

    def termal_button_clicked(self):
        if self.is_termal_on:
            self.turn_off_termal.emit()
            self.termal_button.setText("ВКЛ. ОХЛАЖДЕНИЕ")
            self.termal_button.setStyleSheet("QPushButton"
                                             "{"
                                             "background-color : green;"
                                             "}"
                                             "QPushButton"
                                             "{"
                                             "color : white;"
                                             "}"
                                             "QPushButton::pressed"
                                             "{"
                                             "background-color : grey;"
                                             "}"
                                             )
            self.is_termal_on = False

        else:
            self.turn_on_termal.emit()
            self.termal_start_work.emit()
            self.is_termal_on = True
            self.termal_button.setText("ВЫКЛ. ОХЛАЖДЕНИЕ")
            self.termal_button.setStyleSheet("QPushButton"
                                             "{"
                                             "background-color : red;"
                                             "}"
                                             "QPushButton"
                                             "{"
                                             "color : white;"
                                             "}"
                                             "QPushButton::pressed"
                                             "{"
                                             "background-color : grey;"
                                             "}"
                                             )

    # def termal_off_button_clicked(self):
    #     self.turn_off_termal.emit()

    def print_current_temperature(self, current_temp):
        self.current_termal_temperature = current_temp
        str_temp = "Температура лазера= " + \
            str(current_temp) + " С || " + \
            "Установленная температура лазера = 18 C "

        if self.termal.is_Termal_turn_On:
            str_temp += "|| Охлаждение Включено"
        else:
            str_temp += "|| Охлаждение Выключено"

        self.label_status.setText(str_temp)
###########################

    def from_file_to_list(self, filemane):
        list = []
        file1 = open(filemane, 'r')
        Lines = file1.readlines()

        for line in Lines:
            list.append(float(line))

        return list

    def init_widgets(self):
        self.setWindowIcon(
            QtGui.QIcon('KKL.png'))

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

        # self.graphWidget.getAxis("bottom").setTickSpacing(
        #     levels=[(22, 0)])
        # self.graphWidget.getAxis("left").setTickSpacing(
        #     levels=[(22, 0)])

        ##############

        self.label_status = QLabel("")
        self.label_status.setFrameStyle(QFrame.Panel | QFrame.Sunken)

        self.Xeryon_cbox = QCheckBox("Двигатель")
        self.Termal_cbox = QCheckBox("Охлаждение лазера")
        self.Rigol_cbox = QCheckBox("Осцилограф")

        device_list_layout = QHBoxLayout()
        device_list_layout.addWidget(
            self.Xeryon_cbox, alignment=QtCore.Qt.AlignCenter)
        device_list_layout.addWidget(
            self.Termal_cbox, alignment=QtCore.Qt.AlignCenter)
        device_list_layout.addWidget(
            self.Rigol_cbox, alignment=QtCore.Qt.AlignCenter)

        # Device choice
        self.device_choice = QComboBox(self)
        self.device_choice.addItem("RIGOL Oscilloscope")
        self.device_choice.addItem("Ophir VEGA")

        # NEW
        new_layout = QHBoxLayout()

        self.clear_plot_button = QPushButton(
            "Очистить график",  clicked=self.clear_plot)
        self.clear_plot_button.setMaximumSize(200, 40)
        self.several_plots_enable_cbox = QCheckBox(
            "Отображать прошлые спектры")
        self.several_plots_enable_cbox.setMaximumSize(240, 40)
        new_layout.addWidget(self.several_plots_enable_cbox)
        new_layout.addWidget(self.clear_plot_button)

        plot_layout = QVBoxLayout()
        plot_layout.addLayout(device_list_layout)
        plot_layout.addWidget(self.graphWidget)
        plot_layout.addLayout(new_layout)
        plot_layout.addWidget(self.device_choice)

        #########
        # START

        empty_label = QLabel("")

        start_angle_value_layout = QHBoxLayout()
        self.start_label = QLabel("Начальный угол: ")
        self.start_label.setMaximumSize(200, 40)
        self.start_line_edit = QLineEdit("110.05")
        self.start_line_edit.setMaximumSize(80, 40)
        start_angle_value_layout.addWidget(
            self.start_label, alignment=QtCore.Qt.AlignCenter)
        start_angle_value_layout.addWidget(
            self.start_line_edit, alignment=QtCore.Qt.AlignCenter)

        # STOP
        stop_angle_value_layout = QHBoxLayout()
        self.stop_label = QLabel("Конечный угол: ")
        self.stop_label.setMaximumSize(300, 40)
        self.stop_line_edit = QLineEdit("93.75")
        self.stop_line_edit.setMaximumSize(80, 40)
        stop_angle_value_layout.addWidget(
            self.stop_label, alignment=QtCore.Qt.AlignCenter)
        stop_angle_value_layout.addWidget(
            self.stop_line_edit, alignment=QtCore.Qt.AlignCenter)

        # START STOP BUTOONS
        start_stop_buttons_layout = QHBoxLayout()
        self.start_button = QPushButton(
            "СТАРТ", clicked=self.start_button_clicked)
        self.start_button.setMaximumSize(100, 40)
        self.start_button.setStyleSheet("QPushButton"
                                        "{"
                                        "background-color : green;"
                                        "}"
                                        "QPushButton"
                                        "{"
                                        "color : white;"
                                        "}"
                                        "QPushButton::pressed"
                                        "{"
                                        "background-color : grey;"
                                        "}"
                                        )

        self.stop_button = QPushButton(
            "СТОП",  clicked=self.stop_button_clicked)
        self.stop_button.setMaximumSize(100, 40)
        self.stop_button.setStyleSheet("QPushButton"
                                       "{"
                                       "background-color : red;"
                                       "}"
                                       "QPushButton"
                                       "{"
                                       "color : white;"
                                       "}"
                                       "QPushButton::pressed"
                                       "{"
                                       "background-color : grey;"
                                       "}"
                                       )

        start_stop_buttons_layout.addWidget(self.start_button)
        start_stop_buttons_layout.addWidget(self.stop_button)

        # termal_control_layout = QVBoxLayout()

        self.termal_button = QPushButton("ВКЛ. ОХЛАЖДЕНИЕ")
        self.termal_button.clicked.connect(self.termal_button_clicked)
        self.termal_button.setMaximumSize(200, 80)

        set_ang_layout = QHBoxLayout()

        set_ang_button = QPushButton("Установить угол")
        set_ang_button.setMaximumSize(150, 40)
        set_ang_button.clicked.connect(self.set_ang_button_clicked)
        self.set_ang_line_edit = QLineEdit("101.1")
        self.set_ang_line_edit.setMaximumSize(50, 40)

        set_ang_layout.addWidget(set_ang_button)
        set_ang_layout.addWidget(self.set_ang_line_edit)

        get_intensity_layout = QHBoxLayout()
        get_intensity_label = QLabel("Интенсивность:")
        get_intensity_label.setMaximumSize(110, 40)

        self.intensity_value = QLabel("")
        self.intensity_value.setMaximumSize(50, 40)
        intensity_label_ye = QLabel("у:е")
        intensity_label_ye.setMaximumSize(50, 40)
        self.intensity_value.setFrameStyle(QFrame.Box | QFrame.Plain)
        get_intensity_layout.addWidget(get_intensity_label)
        get_intensity_layout.addWidget(self.intensity_value)
        get_intensity_layout.addWidget(intensity_label_ye)

        save_to_file_button = QPushButton(
            "Сохранить данные\nспектра в файл")
        save_to_file_button.setMaximumSize(200, 80)
        save_to_file_button.clicked.connect(self.save_data_to_file)

        # progress bars
        progress_bars_layout = QVBoxLayout()

        self.step_progress_bar = QProgressBar(self)
        self.step_progress_bar.setMaximumSize(200, 80)
        self.spectrum_progress_bar = QProgressBar(self)
        self.spectrum_progress_bar.setMaximumSize(200, 80)

        progress_bars_layout.addWidget(self.step_progress_bar)
        progress_bars_layout.addWidget(self.spectrum_progress_bar)

        self.logging = QPlainTextEdit()
        self.logging.setMaximumWidth(200)

        clear_logging_button = QPushButton(
            "Очистить терманал",  clicked=self.logging.clear)
        clear_logging_button.setMaximumSize(200, 40)

        control_layout = QVBoxLayout()

        control_layout.addWidget(empty_label)
        control_layout.addLayout(start_angle_value_layout)
        control_layout.addLayout(stop_angle_value_layout)
        control_layout.addLayout(start_stop_buttons_layout)
        # control_layout.addLayout(termal_control_layout)
        control_layout.addLayout(set_ang_layout)
        control_layout.addLayout(get_intensity_layout)

        control_layout.addWidget(
            save_to_file_button)

        control_layout.addLayout(progress_bars_layout)

        control_layout.addWidget(self.logging)
        control_layout.addWidget(clear_logging_button)
        # control_layout.addWidget(self.termal_button)

        layout = QHBoxLayout()
        layout.addLayout(plot_layout)
        layout.addLayout(control_layout)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def close_window(self, event):

        # ret = QtWidgets.QMessageBox.warning(None, 'Внимание!', 'Лазер Выключен?',
        #                                     QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        #                                     QtWidgets.QMessageBox.Yes)
        # if ret == QtWidgets.QMessageBox.Yes:
        #     self.turn_off_termal.emit()
        #     time.sleep(0.2)
        #     QtWidgets.QMainWindow.closeEvent(self, event)
        # else:
        #     QtWidgets.QMainWindow.closeEvent(self, event)
        #     # event.ignore()

        self.termal.is_working = False
        self.rigol.is_working = False
        self.rigol_thread.wait(1000)
        self.termal_thread.wait(1000)


########################
app = QtWidgets.QApplication(sys.argv)
w = MainWindow()
w.show()
sys.exit(app.exec_())
