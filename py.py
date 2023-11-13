import sys
import typing
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout, QProgressBar
from PyQt5.QtCore import QThread, QObject, pyqtSignal as Signal, pyqtSlot as Slot
from PyQt5 import QtCore
import time


from pyqtgraph import PlotWidget, plot
from pyqtgraph.Qt import QtGui
import pyqtgraph as pg

import threading


class Worker(QObject):
    progress = Signal(int)
    completed = Signal(int)
    running = False

    @Slot(int)
    def do_work(self, plotting_data):
        self.running = True
        while self.running:
            time.sleep(1)
            print("in do work\n")
            print(self.running)
            self.progress.emit(plotting_data)

        print("loop finished")

        self.completed.emit(plotting_data)


class MainWindow(QMainWindow):
    work_requested = Signal(int)

    i = 11
    x_value = []
    y_value = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setGeometry(100, 100, 300, 50)
        self.setWindowTitle('QThread Demo')

        self.graphWidget = pg.PlotWidget()
        self.graphWidget.setBackground('w')

        for i in range(0, 10):
            self.x_value.append(i)
            self.y_value.append(i * i)

        # setup widget
        self.widget = QWidget()
        layout = QVBoxLayout()
        self.widget.setLayout(layout)
        self.setCentralWidget(self.widget)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)

        self.btn_start = QPushButton('Start', clicked=self.start)
        self.btn_test = QPushButton('test')

        layout.addWidget(self.graphWidget)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_test)
        ####

        self.worker = Worker()
        self.worker_thread = QThread()

        self.btn_test.clicked.connect(self.test)

        self.worker.progress.connect(self.update_progress)
        self.worker.completed.connect(self.complete)

        self.work_requested.connect(self.worker.do_work)

        # move worker to the worker thread
        self.worker.moveToThread(self.worker_thread)

        # start the thread
        self.worker_thread.start()

        # show the window
        self.show()

    def start(self):
        self.i = 10
        self.btn_start.setEnabled(False)
        self.plotting_data = 1
        self.worker_thread.start()
        self.work_requested.emit(1)

    def update_progress(self, v):
        print("in update progress")
        self.x_value.append(self.i)
        self.y_value.append(1/self.i)
        self.i += 1
        print(self.i)

        self.graphWidget.plot(self.x_value, self.y_value)

    def complete(self, v):
        self.progress_bar.setValue(v)
        self.btn_start.setEnabled(True)

    def test(self):
        print("stop")
        self.worker.running = False


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())


# import sys
# from PyQt5.QtWidgets import QApplication, QWidget, QRadioButton, QVBoxLayout, QLabel

# class RadioButtonApp(QWidget):
#     def __init__(self):
#         super().__init__()

#         self.setWindowTitle("Radio Button Example")
#         self.setGeometry(100, 100, 300, 200)  # (x, y, width, height)

#         layout = QVBoxLayout()

#         # Create radio buttons for options
#         self.option1_radio = QRadioButton("Python", self)
#         self.option2_radio = QRadioButton("Java", self)
#         self.option3_radio = QRadioButton("C++", self)

#         layout.addWidget(self.option1_radio)
#         layout.addWidget(self.option2_radio)
#         layout.addWidget(self.option3_radio)

#         # Create a label to display the selected option
#         self.selected_option_label = QLabel("Selected Option: None", self)
#         layout.addWidget(self.selected_option_label)

#         # Connect the radio buttons' toggled signal to a slot that updates the label
#         self.option1_radio.toggled.connect(lambda: self.update_selected_option("Python"))
#         self.option2_radio.toggled.connect(lambda: self.update_selected_option("Java"))
#         self.option3_radio.toggled.connect(lambda: self.update_selected_option("C++"))

#         self.setLayout(layout)

#     def update_selected_option(self, option):
#         if option:
#             self.selected_option_label.setText(f"Selected Option: {option}")

# def main():
#     app = QApplication(sys.argv)
#     window = RadioButtonApp()
#     window.show()
#     sys.exit(app.exec_())

# if __name__ == "__main__":
#     main()


# from os import system
# import sys
# import os
# import subprocess
# var = os.system("cat /dev/tty21 2> device_error.txt")
# # system("cat hello2.txt")

# print("haha\n")
# # tmp = sys.stdout
# print(var)
# print("haha2\n")

# import subprocess
# output = subprocess.check_output(['cat', '/dev/ttyACM0'])
# print(output)


# # from Xeryon import *
# from pylablib.devices import Ophir
# # import rigol2000a

# import serial, time

# from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QLineEdit, QComboBox
# from PyQt5 import QtWidgets, QtCore
# from PyQt5.QtCore import QThread, QObject, pyqtSignal, pyqtSlot
# from PyQt5.QtGui import QFont

# from pyqtgraph import PlotWidget, plot
# from pyqtgraph.Qt import QtGui
# import pyqtgraph as pg

# import sys
# # import random
# import re
# from threading import Thread


# class MainWindow(QtWidgets.QMainWindow):
#     def __init__(self):
#         QtWidgets.QMainWindow.__init__(self)

#     def closeEvent(self, event):
#         ret = QtWidgets.QMessageBox.question(None, 'Внимание!', 'Лазер Выключен?',
#                                          QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
#                                          QtWidgets.QMessageBox.Yes)
#         if ret == QtWidgets.QMessageBox.Yes:

#             QtWidgets.QMainWindow.closeEvent(self, event)
#         else:
#             event.ignore()


# if __name__ == "__main__":
#     app = QtWidgets.QApplication(sys.argv)
#     ui = MainWindow()
#     ui.show()
#     sys.exit(app.exec_())


# import sys
# from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QComboBox, QPushButton

# class Example(QMainWindow):

#     def __init__(self):
#         super().__init__()

#         combo = QComboBox(self)
#         combo.addItem("Apple")
#         combo.addItem("Pear")
#         combo.addItem("Lemon")

#         combo.move(50, 50)

#         self.qlabel = QLabel(self)
#         self.qlabel.move(50,16)

#         combo.activated[str].connect(self.onChanged)

#         self.setGeometry(50,50,320,200)
#         self.setWindowTitle("QLineEdit Example")
#         self.show()

#     def onChanged(self, text):
#         self.qlabel.setText(text)
#         self.qlabel.adjustSize()

# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     ex = Example()
#     sys.exit(app.exec_())


# def from_file_to_list(filemane):
#         list = []
#         file1 = open(filemane, 'r')
#         Lines = file1.readlines()

#         for line in Lines:
#             list.append(float(line))

#         for i in range(len(list)):
#             print(list[i])
#         return list

# def binary_search(arr, low, high, x):

#     # Check base case
#     if high >= low:

#         mid = (high + low) // 2

#         # If element is present at the middle itself
#         if arr[mid] == x:
#             return mid

#         # If element is smaller than mid, then it can only
#         # be present in left subarray
#         elif arr[mid] > x:
#             return binary_search(arr, low, mid - 1, x)

#         # Else the element can only be present in right subarray
#         else:
#             return binary_search(arr, mid + 1, high, x)

#     else:
#         # Element is not present in the array
#         return -1

# # Test array
# # arr = [ 2, 3, 4, 10, 40 ]
# arr = from_file_to_list("./KKL/sort_angles.txt")
# x = 118.2

# # Function call
# result = binary_search(arr, 0, len(arr)-1, x)

# if result != -1:
#     print("Element is present at index", str(result))
# else:
#     print("Element is not present in array")


# from PyQt5.QtCore import QThread
# from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QLabel, QFrame, QLineEdit
# import sys
# from PyQt5 import QtWidgets, QtCore

# # worker.py
# from PyQt5.QtCore import QThread, QObject, pyqtSignal, pyqtSlot
# import time


# import pyqtgraph as pg
# import numpy as np

# from PyQt5 import QtWidgets, QtCore
# from pyqtgraph import PlotWidget, plot
# import pyqtgraph as pg
# import sys  # We need sys so that we can pass argv to QApplication
# import os
# from random import randint

# class MainWindow(QtWidgets.QMainWindow):

#     def __init__(self, *args, **kwargs):
#         super(MainWindow, self).__init__(*args, **kwargs)

#         self.graphWidget = pg.PlotWidget()
#         self.setCentralWidget(self.graphWidget)

#         start_button = QPushButton("START")
#         start_button.clicked.connect(self.start_button_clicked)

#         self.x = list(range(100))  # 100 time points
#         self.y = [randint(0,100) for _ in range(100)]  # 100 data points

#         self.graphWidget.setBackground('w')

#         pen = pg.mkPen(color=(255, 0, 0))
#         self.data_line =  self.graphWidget.plot(self.x, self.y, pen=pen)

#         self.timer = QtCore.QTimer()
#         self.timer.setInterval(50)
#         self.timer.timeout.connect(self.update_plot_data)
#         self.timer.start()

#     def update_plot_data(self):

#         self.x = self.x[1:]  # Remove the first y element.
#         self.x.append(self.x[-1] + 1)  # Add a new value 1 higher than the last.

#         self.y = self.y[1:]  # Remove the first
#         self.y.append( randint(0,100))  # Add a new random value.

#         self.data_line.setData(self.x, self.y)  # Update the data.


# app = QtWidgets.QApplication(sys.argv)
# w = MainWindow()
# w.show()
# sys.exit(app.exec_())

# class Worker(QObject):
#     finished = pyqtSignal()
#     intReady = pyqtSignal(int)


#     @pyqtSlot()
#     def procCounter(self): # A slot takes no params
#         for i in range(1, 100):
#             time.sleep(1)
#             self.intReady.emit(i)

#         self.finished.emit()


# class Form(QtWidgets.QMainWindow):


#   def __init__(self):
#     super().__init__()
#     self.label = QLabel("0")

#        # 1 - create Worker and Thread inside the Form
#     self.obj = Worker()  # no parent!
#     self.thread = QThread()  # no parent!

#        # 2 - Connect Worker`s Signals to Form method slots to post data.
#     self.obj.intReady.connect(self.onIntReady)

#        # 3 - Move the Worker object to the Thread object
#     self.obj.moveToThread(self.thread)

#        # 4 - Connect Worker Signals to the Thread slots
#     self.obj.finished.connect(self.thread.quit)

#        # 5 - Connect Thread started signal to Worker operational slot method
#     self.thread.started.connect(self.obj.procCounter)

#        # * - Thread finished signal will close the app if you want!
#        #self.thread.finished.connect(app.exit)

#        # 6 - Start the thread
#     self.thread.start()

#     self.timer = QtCore.QTimer()
#     self.timer.setInterval(5000)
#     self.timer.timeout.connect(self.start_button_clicked)
#     self.timer.start()

#        # 7 - Start the form
#     start_button = QPushButton("start")
#    #  start_button.clicked.connect(self.start_button_clicked)


#     layout = QVBoxLayout()
#     layout.addWidget(start_button)
#     layout.addWidget(self.label)

#     widget = QWidget()
#     widget.setLayout(layout)
#     self.setCentralWidget(widget)


#   def onIntReady(self, i):
#     self.label.setText("{}".format(i))
#     #print(i)

#   def start_button_clicked(self):
#      print("start")
#      time.sleep(5)


# ########################
# app = QtWidgets.QApplication(sys.argv)
# w = Form()
# w.show()
# sys.exit(app.exec_())
