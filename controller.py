# -*- coding: utf-8 -*-
"""
Created on Tue Dec 15 16:11:19 2020



@author: Badari
"""
# TODO: Need to check for errors TODO: If heater is already running when program started, the software should show
#  the progress of heating program. Add documentation TODO: Update GUI interface to set temperature manually TODO:
#   There is some problem in either loading previously saved program in instrument, or saving into instrument using
#   feed_program command. It it not saved maybe..

import sys
from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
from PyQt5.QtWidgets import QLabel

from Eurothermdesign import Ui_Eurotherm2408
from eurotherm import Eurotherm
import numpy as np
from serial import SerialException
from time import sleep, localtime, strftime
import os
from pymeasure.experiment import unique_filename


# noinspection PyAttributeOutsideInit
class MainWindow(QtWidgets.QMainWindow, Ui_Eurotherm2408):
    def __init__(self, *args, obj=None, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        # load the UI page
        self.outputData = None
        self.t2 = None
        self.laststep = None
        self.prestep = None
        self.current_status = None  # will be initialized in get_instrument()
        self.obj = obj
        self.fname = None
        self.fed_data_flag = False
        self.fileName = None
        self.instrument_connect_flag = False
        self.setupUi(self)
        self.x = [0.0]
        self.stepno = 0
        self.current_Temp = 0.0  # program to save current temperature in this variable
        self.set_Temp = 0.0
        self.total_time = 0
        self.time_left = 0
        self.instrument_address = "COM4"
        self.OP = 0
        self.hold = False
        self.run_status = False
        self.step1 = {'T': 0.0, 'Rt': 0.0, 'Rr': 0.0, 'H': 0.0, 'E': 2}
        self.step2 = {'T': 0.0, 'Rt': 0.0, 'Rr': 0.0, 'H': 0.0, 'E': 2}
        self.step3 = {'T': 0.0, 'Rt': 0.0, 'Rr': 0.0, 'H': 0.0, 'E': 2}
        self.clear_parameters()
        self.asteps = [self.step1, self.step2, self.step3]
        self.exit_menu()  # initiate the action for exit button in menubar
        self.save_menu()  # initiate the dialogue for save program button in menubar
        self.open_menu()  # initiate the dialogue for open program button in menubar
        self.new_menu()  # initiate the dialogue for new program button in menubar
        self.com1_menu()
        self.com2_menu()
        self.com3_menu()
        self.com4_menu()
        self.Enter_Manually_menu()
        self.initialize_plot()
        self.pushButton.setEnabled(False)
        self.pushButton_2.setEnabled(False)  #
        self.pushButton_3.setEnabled(False)  #
        self.pushButton_4.setEnabled(False)
        self.pushButton_7.setEnabled(False)
        self.doubleSpinBox_3.setReadOnly(True)
        self.doubleSpinBox_7.setReadOnly(True)
        self.doubleSpinBox_11.setReadOnly(True)
        self.doubleSpinBox_2.setSingleStep(0.1)
        self.doubleSpinBox_6.setSingleStep(0.1)
        self.doubleSpinBox_10.setSingleStep(0.1)
        self.pushButton_7.clicked.connect(self.feed_parameters)
        self.pushButton_6.clicked.connect(self.connect_instrument)
        self.pushButton.clicked.connect(self.run_program)
        self.pushButton_2.clicked.connect(self.stop_program)
        self.pushButton_3.clicked.connect(self.hold_program)
        self.pushButton_4.clicked.connect(self.continue_program)
        self.pushButton_5.clicked.connect(self.clear_parameters)
        self.doubleSpinBox_2.valueChanged['double'].connect(lambda: self.Rt_to_Rr(
            self.current_Temp, self.doubleSpinBox.value(), self.doubleSpinBox_2, self.doubleSpinBox_3))
        self.doubleSpinBox.valueChanged['double'].connect(lambda: self.Rt_to_Rr(
            self.current_Temp, self.doubleSpinBox.value(), self.doubleSpinBox_2, self.doubleSpinBox_3))
        self.doubleSpinBox_6.valueChanged['double'].connect(lambda: self.Rt_to_Rr(
            self.doubleSpinBox.value(), self.doubleSpinBox_5.value(), self.doubleSpinBox_6, self.doubleSpinBox_7))
        self.doubleSpinBox_5.valueChanged['double'].connect(lambda: self.Rt_to_Rr(
            self.doubleSpinBox.value(), self.doubleSpinBox_5.value(), self.doubleSpinBox_6, self.doubleSpinBox_7))
        self.doubleSpinBox_10.valueChanged['double'].connect(lambda: self.Rt_to_Rr(
            self.doubleSpinBox_5.value(), self.doubleSpinBox_9.value(), self.doubleSpinBox_10, self.doubleSpinBox_11))
        self.doubleSpinBox_9.valueChanged['double'].connect(lambda: self.Rt_to_Rr(
            self.doubleSpinBox_5.value(), self.doubleSpinBox_9.value(), self.doubleSpinBox_10, self.doubleSpinBox_11))
        os.chdir(os.path.join(os.path.expandvars("%userprofile%"), "Desktop"))
        self.program_finish_status = False
        self.show()
        self.eth = None  # will be initialized in connect_instrument()
        self.instID = None  # will be initialized in connect_instrument()
        self.connect_instrument()

    def connect_instrument(self):
        try:
            self.eth = Eurotherm(self.instrument_address)
            self.instID = self.eth.read_param('II')
            if self.instID == '>2480':
                self.statusBar().showMessage(
                    'Successfully connected to Eurotherm2408. Waiting to feed parameters..')
                self.current_Temp = float(self.eth.read_param('PV'))
                self.instrument_connect_flag = True
                self.pushButton_5.setEnabled(True)
                self.pushButton_6.setEnabled(False)
                self.pushButton.setEnabled(True)
                self.pushButton_7.setEnabled(True)
                self.menuAddress.setDisabled(True)
                # set ramp rate unit as minutes
                self.eth.write_param('d0', '1')
                # set dwell time unit as minutes
                self.eth.write_param('p0', '1')
                self.get_controller_data()  # get current program present in the controller
                self.get_instrument_status()
                self.display_status()  # display all the current status of the controller
                if self.current_status == 1:  # RESET
                    self.eth.write_param('EP', '1')  # set program number as 1
                elif self.current_status in (8, 16):
                    self.eth.write_param('PC', '1')  # Reset the program
                    self.eth.write_param('EP', '1')  # set program number as 1
                elif self.current_status == 2 or self.current_status == 4:
                    self.display_current_heating_program()
            else:
                self.statusBar().showMessage(
                    'Wrong Instrument! Change address to correct instrument and retry!', 5000)
                self.instrument_connect_flag = False
                inst = QtWidgets.QDialog(self)
                inst.resize(400, 60)
                hl = QtWidgets.QHBoxLayout(inst)
                inst.setWindowTitle("Wrong Instrument...")
                l: QLabel = QtWidgets.QLabel(inst)
                l.setText(
                    "Wrong Instrument connected!\n Please enter the correct address for Eurotherm 2408")
                hl.addWidget(l)
                inst.exec_()
                self.eth.s.close()
        except SerialException:
            self.instrument_connect_flag = False
            inst = QtWidgets.QDialog(self)
            inst.resize(400, 60)
            hl = QtWidgets.QHBoxLayout(inst)
            inst.setWindowTitle("Error Connecting Instrument...")
            l: QLabel = QtWidgets.QLabel(inst)
            l.setText(
                "The instrument was not found at this address\n Please try different address or check instrument "
                "connection")
            hl.addWidget(l)
            inst.exec_()

    def enable_editing(self):
        self.program_finish_status = False
        self.pushButton_2.setEnabled(True)
        self.pushButton_3.setEnabled(True)
        self.pushButton_4.setEnabled(True)
        self.pushButton.setEnabled(False)
        self.pushButton_5.setEnabled(False)
        self.pushButton_6.setEnabled(False)
        self.pushButton_7.setEnabled(False)
        self.doubleSpinBox.setEnabled(False)
        self.doubleSpinBox_2.setEnabled(False)
        self.doubleSpinBox_3.setEnabled(False)
        self.doubleSpinBox_4.setEnabled(False)
        self.doubleSpinBox_5.setEnabled(False)
        self.doubleSpinBox_6.setEnabled(False)
        self.doubleSpinBox_7.setEnabled(False)
        self.doubleSpinBox_8.setEnabled(False)
        self.doubleSpinBox_9.setEnabled(False)
        self.doubleSpinBox_10.setEnabled(False)
        self.doubleSpinBox_11.setEnabled(False)
        self.doubleSpinBox_12.setEnabled(False)
        self.comboBox.setEnabled(False)
        self.comboBox_2.setEnabled(False)
        self.comboBox_3.setEnabled(False)

    def display_current_heating_program(self):
        # Display and continue a currently running heater program
        self.enable_editing()
        self.initialize_plot_data(continuation=True)
        self.plot()
        # so, elapsed time = total_time - time remaining in current segment - time for future segments
        # program_remaining_time = float(self.eth.read_param('TP'))
        # print(self.eth.read_param('TP'),self.total_time)
        self.plot_realtime_data()
        self.statusBar().showMessage('Program is running..')
        self.run_status = True
        self.fed_data_flag = False

    def feed_parameters(self):
        if not self.instrument_connect_flag:
            self.connect_instrument()
        if not self.instrument_connect_flag:
            return 0
        self.statusBar().showMessage('Feeding the data into the controller. Please wait..')
        self.get_parameters()
        self.get_instrument_status()
        self.initialize_plot_data()
        self.send_parameters()
        self.fed_data_flag = True
        # If you want to update the saved file, uncomment this
        # if self.fileName:
        #    self.savefile()
        self.plot()
        self.statusBar().showMessage(
            'Finished loading the program into controller. Click RUN to start!')
        self.display_status()

    def run_program(self):
        # run the program only if the instrument is successfully connected
        # TODO: if program is already running, stop it, and then start.
        if not self.instrument_connect_flag:
            self.connect_instrument()
        if not self.instrument_connect_flag:
            return 0
        self.feed_parameters()
        self.enable_editing()
        self.plot_realtime_data()
        # send command to instrument to start the heating program
        self.eth.write_param('PC', '2')
        self.statusBar().showMessage('Program is running..')
        self.run_status = True
        with open(self.fname, 'a', newline='') as f:
            f.write("\n\n0, Starting new heating program")
        self.fed_data_flag = False

    def stop_program(self):
        self.pushButton.setEnabled(True)
        self.pushButton_4.setEnabled(True)
        self.pushButton_5.setEnabled(True)
        self.pushButton_7.setEnabled(True)
        self.doubleSpinBox.setEnabled(True)
        self.doubleSpinBox_2.setEnabled(True)
        self.doubleSpinBox_3.setEnabled(True)
        self.doubleSpinBox_4.setEnabled(True)
        self.doubleSpinBox_5.setEnabled(True)
        self.doubleSpinBox_6.setEnabled(True)
        self.doubleSpinBox_7.setEnabled(True)
        self.doubleSpinBox_8.setEnabled(True)
        self.doubleSpinBox_9.setEnabled(True)
        self.doubleSpinBox_10.setEnabled(True)
        self.doubleSpinBox_11.setEnabled(True)
        self.doubleSpinBox_12.setEnabled(True)
        self.comboBox.setEnabled(True)
        self.comboBox_2.setEnabled(True)
        self.comboBox_3.setEnabled(True)
        self.pushButton_2.setEnabled(False)
        self.pushButton_2.setEnabled(False)
        self.pushButton_3.setEnabled(False)
        self.pushButton_4.setEnabled(False)
        self.timer.stop()
        self.eth.write_param('PC', '1')
        self.run_status = False
        self.statusBar().showMessage('User has stopped the program.')
        t = localtime()
        elapsed_time = strftime("%H:%M:%S", t)
        with open(self.fname, 'a', newline='') as f:
            f.write(f"\n{elapsed_time}, Stopped the heater")
        sleep(1)
        self.get_instrument_status()
        self.display_status()
        # self.save_heating_info()

    def save_heating_info(self, elapsed_time, set_Temp, current_Temp, OP):
        # save heating data to file
        if self.fname is None:
            print("Hello I was here")
            self.fname = unique_filename('C:\\HeatingData', prefix='HeatingData_', ext='csv',
                                         index=False, datetimeformat="%Y-%m-%d-%Hh%Mm")
            with open(self.fname, 'w', newline='') as f:
                f.write("Elapsed Time(s),Set Temperature(°C),Temperature(°C),Output(%)")
        with open(self.fname, 'a', newline='') as f:
            f.write(f"\n{elapsed_time},{set_Temp},{current_Temp},{OP}")

    def hold_program(self):
        self.hold = True
        self.pushButton_3.setEnabled(False)
        self.statusBar().showMessage('User has paused the program.')
        t = localtime()
        elapsed_time = strftime("%H:%M:%S", t)
        with open(self.fname, 'a', newline='') as f:
            f.write(f"\n{elapsed_time}, Heating paused")
        # send command to instrument to pause the program
        self.eth.write_param('PC', '4')

    def continue_program(self):
        if self.hold:
            self.pushButton_3.setEnabled(True)
            self.eth.write_param('PC', '2')  # continue the paused program
            self.hold = False
            t = localtime()
            elapsed_time = strftime("%H:%M:%S", t)
            with open(self.fname, 'a', newline='') as f:
                f.write(f"\n{elapsed_time}, Continue heating.")
        else:
            self.eth.write_param('PC', '4')
            self.total_time = self.total_time - float(self.eth.read_param('TS')) / 3600
            sleep(0.2)
            # make remaining time in current segment as just 1 sec,
            self.eth.write_param('TS', '1')
            # so that the program quickly jumps to next step in the program
            sleep(0.2)
            self.eth.write_param('PC', '2')
            t = localtime()
            elapsed_time = strftime("%H:%M:%S", t)
            with open(self.fname, 'a', newline='') as f:
                f.write(f"\n{elapsed_time}, Jump to next step.")
        self.statusBar().showMessage('Program is running..')

    def get_instrument_status(self):
        self.current_Temp = float(self.eth.read_param('PV'))
        self.OP = float(self.eth.read_param('OP'))
        self.set_Temp = float(self.eth.read_param('SL'))
        self.current_status = int(float(self.eth.read_param('PC')))
        self.time_left = self.total_time - self.x[-1]
        if self.time_left < 0:
            self.time_left = 0

    def get_controller_data(self):
        # program to load already stored data from the PID controller
        ID = ['1', '2', '3', '4', '5', '6', '7', '8',
              '9', ':', ';', '<', '=', '>', '?', '@']
        self.clear_parameters()
        i = 0
        st = 0
        s_type = float(self.eth.read_param('$' + ID[i]))
        while s_type and i < 7:
            if s_type == 1:  # ramp rate
                self.asteps[st]['T'] = float(self.eth.read_param('s' + ID[i]))
                rate = float(self.eth.read_param('d' + ID[i]))
                self.asteps[st]['Rt'] = (
                                                self.asteps[st]['T'] - self.current_Temp) / (60 * rate)
                next_stype = float(self.eth.read_param('$' + ID[i + 1]))
                if next_stype in (1, 2):
                    self.asteps[st]['H'] = 0
                    self.asteps[st]['E'] = 0
                    st = st + 1
                elif next_stype == 0:
                    self.asteps[st]['E'] = int(
                        float(self.eth.read_param('p' + ID[i + 1])) + 1)
                    break
            elif s_type == 2:  # ramp time
                self.asteps[st]['T'] = float(self.eth.read_param('s' + ID[i]))
                self.asteps[st]['Rt'] = float(
                    self.eth.read_param('d' + ID[i])) / 60
                next_stype = float(self.eth.read_param('$' + ID[i + 1]))
                if next_stype in (1, 2):
                    self.asteps[st]['H'] = 0
                    self.asteps[st]['E'] = 0
                    st = st + 1
                elif next_stype == 0:
                    self.asteps[st]['E'] = int(
                        float(self.eth.read_param('p' + ID[i + 1])) + 1)
                    break
            elif s_type == 3:  # Dwell
                self.asteps[st]['H'] = float(self.eth.read_param('d' + ID[i])) / 60
                if float(self.eth.read_param('$' + ID[i + 1])) == 0:
                    self.asteps[st]['E'] = int(
                        float(self.eth.read_param('p' + ID[i + 1])) + 1)
                    break
                else:
                    self.asteps[st]['E'] = 0
                st = st + 1
            else:
                pass
            i = i + 1
            s_type = float(self.eth.read_param('$' + ID[i]))
        self.step1 = self.asteps[0]
        self.step2 = self.asteps[1]
        self.step3 = self.asteps[2]
        self.load_settings()

    def display_status(self):
        # display the target temperature for current segment
        self.label_19.setText(
            "<html><head/><body><p><span style=\" font-size:10pt;\">{0} ℃</span></p></body></html>".format(
                self.set_Temp))
        # display the current temperature
        self.label_20.setText(
            "<html><head/><body><p><span style=\" font-size:10pt;\">{0} ℃</span></p></body></html>".format(
                self.current_Temp))
        # Display the calculated total program run time
        self.label_18.setText(
            "<html><head/><body><p><span style=\" font-size:10pt;\">{:.3f} H</span></p></body></html>".format(
                self.total_time))
        # display the remaining time for the program to end
        self.label_17.setText(
            "<html><head/><body><p><span style=\" font-size:10pt;\">{:.3f} H</span></p></body></html>".format(
                self.time_left))
        # display the current output power being used
        self.label_16.setText(
            "<html><head/><body><p><span style=\" font-size:10pt;\">{0} %</span></p></body></html>".format(self.OP))
        # display instrument address
        self.label_21.setText(
            "<html><head/><body><p><span style=\" font-size:10pt;\">{0}</span></p></body></html>".format(
                self.instrument_address))
        t = localtime()
        elapsed_time = strftime("%H:%M:%S", t)
        self.save_heating_info(elapsed_time, self.set_Temp, self.current_Temp, self.OP)
        # highlight the current step number
        if self.run_status:
            try:
                self.prestep = self.stepno
                n = int(float(self.eth.read_param('SN')))  # segment number
                stype = int(float(self.eth.read_param('CS')))  # segment type
                if stype == 3:
                    if n % 2 == 0:
                        self.stepno = int(n / 2)
                    else:
                        self.stepno = int(n / 2) + 1
                elif stype in (1, 2) and n % 2 == 0:
                    self.stepno = n
                else:
                    self.stepno = int(n / 2) + 1
                if self.prestep != self.stepno:
                    if self.stepno == 1:
                        self.label_2.setStyleSheet(
                            "background-color: lightgreen")
                        self.label_3.setStyleSheet("")
                        self.label_4.setStyleSheet("")
                    elif self.stepno == 2:
                        self.label_3.setStyleSheet(
                            "background-color: lightgreen")
                        self.label_2.setStyleSheet("")
                        self.label_4.setStyleSheet("")
                    elif self.stepno == 3:
                        self.label_4.setStyleSheet(
                            "background-color: lightgreen")
                        self.label_2.setStyleSheet("")
                        self.label_2.setStyleSheet("")
            except TypeError:
                pass

    def clear_parameters(self):
        self.doubleSpinBox.setValue(0.0)
        self.doubleSpinBox_2.setValue(0.0)
        self.doubleSpinBox_3.setValue(0.0)
        self.doubleSpinBox_4.setValue(0.0)
        self.doubleSpinBox_5.setValue(0.0)
        self.doubleSpinBox_6.setValue(0.0)
        self.doubleSpinBox_7.setValue(0.0)
        self.doubleSpinBox_8.setValue(0.0)
        self.doubleSpinBox_9.setValue(0.0)
        self.doubleSpinBox_10.setValue(0.0)
        self.doubleSpinBox_11.setValue(0.0)
        self.doubleSpinBox_12.setValue(0.0)
        self.comboBox.setCurrentIndex(2)
        self.comboBox_2.setCurrentIndex(2)
        self.comboBox_3.setCurrentIndex(2)
        self.step1 = {'T': 0.0, 'Rt': 0.0, 'Rr': 0.0, 'H': 0.0, 'E': 2}
        self.step2 = {'T': 0.0, 'Rt': 0.0, 'Rr': 0.0, 'H': 0.0, 'E': 2}
        self.step3 = {'T': 0.0, 'Rt': 0.0, 'Rr': 0.0, 'H': 0.0, 'E': 2}

    @staticmethod
    def Rt_to_Rr(t1, t2, db1, db2):
        if db1.value() != 0:
            db2.setValue((t2 - t1) / (60.0 * db1.value()))

    def get_parameters(self):
        self.step1['T'] = self.doubleSpinBox.value()
        self.step1['Rt'] = self.doubleSpinBox_2.value()
        self.step1['Rr'] = self.doubleSpinBox_3.value()
        self.step1['H'] = self.doubleSpinBox_4.value()
        self.step1['E'] = self.comboBox.currentIndex()
        self.step2['T'] = self.doubleSpinBox_5.value()
        self.step2['Rt'] = self.doubleSpinBox_6.value()
        self.step2['Rr'] = self.doubleSpinBox_7.value()
        self.step2['H'] = self.doubleSpinBox_8.value()
        self.step2['E'] = self.comboBox_2.currentIndex()
        self.step3['T'] = self.doubleSpinBox_9.value()
        self.step3['Rt'] = self.doubleSpinBox_10.value()
        self.step3['Rr'] = self.doubleSpinBox_11.value()
        self.step3['H'] = self.doubleSpinBox_12.value()
        self.step3['E'] = self.comboBox_3.currentIndex()
        if self.step1['E'] != 0:
            self.laststep = 1
        elif self.step2['E'] != 0:
            self.laststep = 2
        else:
            self.laststep = 3
            self.step3['E'] = 2
        self.asteps = [self.step1, self.step2, self.step3]

    def send_parameters(self):
        ID = ['1', '2', '3', '4', '5', '6', '7', '8',
              '9', ':', ';', '<', '=', '>', '?', '@']
        ls = 0
        i = 0
        print(self.asteps)
        while self.laststep > ls:
            self.eth.write_param('$' + ID[i], '2')
            self.eth.write_param('s' + ID[i], str(self.asteps[ls]['T']))
            self.eth.write_param('d' + ID[i], str(self.asteps[ls]['Rt'] * 60.0))
            if self.asteps[ls]['H'] != 0:
                i = i + 1
                self.eth.write_param('$' + ID[i], '3')
                self.eth.write_param('d' + ID[i], str(self.asteps[ls]['H'] * 60.0))
            if self.laststep == ls + 1:
                i = i + 1
                self.eth.write_param('$' + ID[i], '0')
                self.eth.write_param('p' + ID[i], str(self.asteps[ls]['E'] - 1))
            ls = ls + 1
            i = i + 1

    def new_menu(self):
        # Suppose you want to start a new program, and want the heater to continue 
        # directly from the current temperature, this function is useful.
        self.actionNew.setShortcut('Ctrl+N')
        self.actionNew.setStatusTip(
            'Enter and run new heating parameters, which will instantly take over from the current heating program')
        self.actionNew.triggered.connect(self.open_new_parameter_file)
        self.fname = unique_filename('C:\\HeatingData', prefix='HeatingData_', ext='csv',
                                     index=False, datetimeformat="%Y-%m-%d-%Hh%Mm")
        with open(self.fname, 'w', newline='') as f:
            f.write("Elapsed Time(s),Set Temperature(°C),Temperature(°C),Output(%)")

    def open_new_parameter_file(self):
        self.clear_parameters()
        # prepare the software to input new values.
        # Note: Even though the software has stopped, the heater program is still running in the instrument
        # Once Run is clicked, the newly fed program will take over, thereby resulting in no lag in the program
        if self.run_status:
            self.pushButton.setEnabled(True)
            self.pushButton_4.setEnabled(True)
            self.pushButton_5.setEnabled(True)
            self.pushButton_7.setEnabled(True)
            self.doubleSpinBox.setEnabled(True)
            self.doubleSpinBox_2.setEnabled(True)
            self.doubleSpinBox_3.setEnabled(True)
            self.doubleSpinBox_4.setEnabled(True)
            self.doubleSpinBox_5.setEnabled(True)
            self.doubleSpinBox_6.setEnabled(True)
            self.doubleSpinBox_7.setEnabled(True)
            self.doubleSpinBox_8.setEnabled(True)
            self.doubleSpinBox_9.setEnabled(True)
            self.doubleSpinBox_10.setEnabled(True)
            self.doubleSpinBox_11.setEnabled(True)
            self.doubleSpinBox_12.setEnabled(True)
            self.comboBox.setEnabled(True)
            self.comboBox_2.setEnabled(True)
            self.comboBox_3.setEnabled(True)
            self.pushButton_2.setEnabled(False)
            self.pushButton_2.setEnabled(False)
            self.pushButton_3.setEnabled(False)
            self.pushButton_4.setEnabled(False)
            self.timer.stop()
            self.run_status = False
            self.statusBar().showMessage(
                'Enter new parameters and click run. If you want to go back to the heater program, restart the '
                'software.')
            # self.get_instrument_status()
            # self.display_status()
            # self.save_heating_info()
        # options = QtWidgets.QFileDialog.Options() options |= QtWidgets.QFileDialog.DontUseNativeDialog
        # self.fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self,"QFileDialog.getSaveFileName()","",
        # "All Files (*);;Parameter Files (*.txt)", options=options)

    def open_menu(self):
        self.actionOpen.setShortcut('Ctrl+O')
        self.actionOpen.setStatusTip('Load parameters saved in a file')
        self.actionOpen.triggered.connect(self.load_parameters_from_file)

    def load_parameters_from_file(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "QFileDialog.getOpenFileNames()", "", "All Files (*);;Parameter Files (*.txt)", options=options)
        if files:
            params = []
            with open(files[0], 'r') as file:
                lines = file.readlines()
                for line in lines:
                    if self.isfloat(line.split()[0]):
                        lp = line.split()
                        params.append([float(lp[1]), float(
                            lp[2]), float(lp[3]), int(lp[4])])
            if params:
                self.clear_parameters()
                l = len(params)
                if l > 0:
                    self.step1['T'] = params[0][0]
                    self.step1['Rt'] = params[0][1]
                    self.step1['H'] = params[0][2]
                    self.step1['E'] = params[0][3]
                    if l == 1 and self.step1['E'] == 0:
                        self.step1['E'] = 1
                    elif self.step1['E'] > 3:
                        self.step1['E'] = 1
                if l > 1:
                    self.step2['T'] = params[1][0]
                    self.step2['Rt'] = params[1][1]
                    self.step2['H'] = params[1][2]
                    self.step2['E'] = params[1][3]
                    if l == 2 and self.step2['E'] == 0:
                        self.step2['E'] = 1
                    elif self.step2['E'] > 3:
                        self.step2['E'] = 1
                if l > 2:
                    self.step3['T'] = params[2][0]
                    self.step3['Rt'] = params[2][1]
                    self.step3['H'] = params[2][2]
                    self.step3['E'] = params[2][3]
                    if self.step3['E'] == 0:
                        self.step3['E'] = 1
                    elif self.step3['E'] > 3:
                        self.step3['E'] = 1
                if l > 3:
                    exstep = QtWidgets.QDialog(self)
                    exstep.resize(450, 77)
                    hl = QtWidgets.QHBoxLayout(exstep)
                    exstep.setWindowTitle("Too many steps")
                    l = QtWidgets.QLabel(exstep)
                    l.setText(
                        "Only three steps can be loaded in this program. Remaining steps are ignored!")
                    hl.addWidget(l)
                    exstep.exec_()
            self.asteps = [self.step1, self.step2, self.step3]
            self.load_settings()

    def save_menu(self):
        self.actionSave.setShortcut('Ctrl+S')
        self.actionSave.setStatusTip('Save the current parameters to file')
        self.actionSave.triggered.connect(self.save_parameters_to_file)

    def save_parameters_to_file(self):
        self.get_parameters()
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        self.fileName, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "QFileDialog.getSaveFileName()", "", "All Files (*);;Parameter Files (*.txt)", options=options)
        if self.fileName:
            self.savefile()

    def savefile(self):
        if self.fileName.find('.') == -1:
            self.fileName = self.fileName + '.txt'
        else:
            index = self.fileName.rindex('.')
            self.fileName = self.fileName[:index] + '.txt'
        with open(self.fileName, 'w') as file:
            file.write("Step\tTemp\tRampt\tHold\tEnd\n")
            if self.laststep > 0:
                txt = '1\t{0}\t{1}\t{2}\t{3}\n'.format(
                    self.step1['T'], self.step1['Rt'], self.step1['H'], self.step1['E'])
                file.write(txt)
            if self.laststep > 1:
                txt = '2\t{0}\t{1}\t{2}\t{3}\n'.format(
                    self.step2['T'], self.step2['Rt'], self.step2['H'], self.step2['E'])
                file.write(txt)
            if self.laststep > 2:
                txt = '3\t{0}\t{1}\t{2}\t{3}\n'.format(
                    self.step3['T'], self.step3['Rt'], self.step3['H'], self.step3['E'])
                file.write(txt)

    def exit_menu(self):  # define exit menu button
        self.actionExit.setShortcut('Ctrl+Q')
        self.actionExit.setStatusTip('Exit application')
        try:
            self.actionExit.triggered.connect(self.eth.s.close)
            self.actionExit.triggered.connect(self.store_software_close_event)
        except AttributeError:
            pass
        self.actionExit.triggered.connect(QtWidgets.qApp.quit)

    def com1_menu(self):
        self.actioncom1.setStatusTip('Set instrument address as \'COM1\'')
        self.actioncom1.triggered.connect(
            lambda: self.set_instrument_address('COM1'))

    def com2_menu(self):
        self.actioncom2.setStatusTip('Set instrument address as \'COM2\'')
        self.actioncom2.triggered.connect(
            lambda: self.set_instrument_address('COM2'))

    def com3_menu(self):
        self.actioncom3.setStatusTip('Set instrument address as \'COM3\'')
        self.actioncom3.triggered.connect(
            lambda: self.set_instrument_address('COM3'))

    def com4_menu(self):
        self.actioncom4.setStatusTip('Set instrument address as \'COM4\'')
        self.actioncom4.triggered.connect(
            lambda: self.set_instrument_address('COM4'))

    def set_instrument_address(self, addr):
        self.instrument_address = addr
        self.label_21.setText(
            "<html><head/><body><p><span style=\" font-size:10pt;\">{0}</span></p></body></html>".format(
                self.instrument_address))

    def Enter_Manually_menu(self):
        self.actionEnter_Manually.setStatusTip(
            'Manually enter instrument address (Enter the full address)')
        self.actionEnter_Manually.triggered.connect(self.manual_entry_dialogue)

    def manual_entry_dialogue(self):
        dlg = QtWidgets.QDialog(self)
        dlg.resize(251, 77)
        gridLayout = QtWidgets.QGridLayout(dlg)
        bb = QtWidgets.QDialogButtonBox(dlg)
        bb.setOrientation(QtCore.Qt.Horizontal)
        bb.setStandardButtons(
            QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        dlg.setWindowTitle("Manual Entry")
        l = QtWidgets.QLabel(dlg)
        l.setText("Enter Instrument Address")
        le = QtWidgets.QLineEdit(dlg)
        gridLayout.addWidget(l, 0, 0)
        gridLayout.addWidget(le, 0, 1)
        gridLayout.addWidget(bb, 1, 0, 1, 1)
        retval = dlg.exec_()
        name = le.text()
        if retval == 1:
            self.set_instrument_address(name)

    def load_settings(self):
        self.laststep = 0
        if self.step1['E'] != 0:
            self.laststep = 1
        elif self.step2['E'] != 0:
            self.laststep = 2
        else:
            self.laststep = 3
            # program is forced to end with reset after step3, if none others are so
            self.step3['E'] = 2
        self.doubleSpinBox.setValue(self.step1['T'])
        self.doubleSpinBox_2.setValue(self.step1['Rt'])
        self.Rt_to_Rr(self.current_Temp, self.doubleSpinBox.value(),
                      self.doubleSpinBox_2, self.doubleSpinBox_3)
        self.doubleSpinBox_4.setValue(self.step1['H'])
        self.comboBox.setCurrentIndex(self.step1['E'])
        self.doubleSpinBox_5.setValue(self.step2['T'])
        self.doubleSpinBox_6.setValue(self.step2['Rt'])
        self.Rt_to_Rr(self.doubleSpinBox.value(), self.doubleSpinBox_5.value(
        ), self.doubleSpinBox_6, self.doubleSpinBox_7)
        self.doubleSpinBox_8.setValue(self.step2['H'])
        self.comboBox_2.setCurrentIndex(self.step2['E'])
        self.doubleSpinBox_9.setValue(self.step3['T'])
        self.doubleSpinBox_10.setValue(self.step3['Rt'])
        self.Rt_to_Rr(self.doubleSpinBox_5.value(), self.doubleSpinBox_9.value(
        ), self.doubleSpinBox_10, self.doubleSpinBox_11)
        self.doubleSpinBox_12.setValue(self.step3['H'])
        self.comboBox_3.setCurrentIndex(self.step3['E'])

    def initialize_plot(self):
        styles = {'color': 'r', 'font-size': '20px'}
        self.graphWidget.setLabel('left', 'Temperature (°C)', **styles)
        self.graphWidget.setLabel('bottom', 'Time (H)', **styles)
        self.graphWidget.addLegend(offset=(180, 170))
        self.graphWidget.showGrid(x=True, y=True)

    def plot(self):
        self.graphWidget.clear()
        pen1 = pg.mkPen(color=(255, 0, 0), width=6)
        self.graphWidget.plot(self.xpoints, self.set_t,
                              name="Set T path", pen=pen1)

    def plot_realtime_data(self):
        self.x = [0]
        self.t2 = [self.current_Temp]
        self.outputData = [0.0]
        pen2 = pg.mkPen(color=(0, 0, 255), width=2)
        try:
            if self.data_line:
                self.data_line.setData(self.x, self.t2)
                if self.fed_data_flag:
                    self.data_line = self.graphWidget.plot(
                        self.x, self.t2, name="Actual T Path", pen=pen2)
                else:
                    self.data_line = self.graphWidget.plot(
                        self.x, self.t2, pen=pen2)
        except (NameError, AttributeError):
            self.data_line = self.graphWidget.plot(
                self.x, self.t2, name="Actual T path", pen=pen2)
        self.timer = QtCore.QTimer()
        self.timecount = QtCore.QElapsedTimer()
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.update_plot_data)
        self.timer.start()
        self.timecount.start()

    def update_plot_data(self):
        self.x.append(self.x[0] + self.timecount.elapsed() / (1000 * 3600))
        self.get_instrument_status()
        self.outputData.append(self.OP)
        self.t2.append(self.current_Temp)
        self.data_line.setData(self.x, self.t2)
        if self.OP > 50:
            if (self.set_Temp - self.current_Temp) / self.set_Temp * 100 > 5:
                self.stop_program()
                self.statusBar().showMessage(
                    'The there is some problem with heater or thermocouple reading. Heating Stopped.')
        self.display_status()
        if self.time_left <= 0 and self.program_finish_status is False:
            self.program_finish_status = True
            self.statusBar().showMessage(
                'The program has successfully finished. Plotter will run until temperature cools down to 50 °C.')
        if self.current_Temp < 50 and self.program_finish_status is True:
            sleep(1)
            self.stop_program()
            self.statusBar().showMessage('The program has successfully finished.')

    def initialize_plot_data(self, continuation=False):
        self.total_time = 0
        self.npoints = 10
        seg = 0
        if continuation:
            # get current segment that is running
            seg = int(float(self.eth.read_param('SN')))
            stype = int(float(self.eth.read_param('CS')))
            if stype == 1 and seg % 2 == 0:
                seg = seg + 1
        if self.laststep > 0:
            time_remaining = self.step1['Rt']
            if seg < 1:
                self.x1r = np.linspace(0, self.step1['Rt'], self.npoints)
                self.t1r = np.linspace(
                    self.current_Temp, self.step1['T'], self.npoints)
            elif seg == 1:
                time_remaining = round(float(self.eth.read_param('TS')) / 3600, 6)
                self.x1r = np.linspace(0, time_remaining, self.npoints)
                self.t1r = np.linspace(
                    self.current_Temp, self.step1['T'], self.npoints)
            else:
                self.x1r = []
                self.t1r = []
            self.xpoints = self.x1r.copy()
            self.set_t = self.t1r.copy()
            self.total_time = self.total_time + time_remaining
            if self.step1['H'] > 0:
                time_remaining = self.step1['H']
                if seg < 2:
                    self.x1h = np.linspace(
                        self.x1r[-1], self.x1r[-1] + self.step1['H'], self.npoints)
                    self.t1h = np.linspace(
                        self.t1r[-1], self.step1['T'], self.npoints)
                elif seg == 2:
                    time_remaining = round(float(self.eth.read_param('TS')) / 3600, 6)
                    self.x1h = np.linspace(
                        0, time_remaining, self.npoints)
                    self.x1h = np.insert(self.x1h, 0, 0)
                    self.t1h = np.linspace(
                        self.step1['T'], self.step1['T'], self.npoints)
                    self.t1h = np.insert(self.t1h, 0, 0)
                else:
                    self.x1h = []
                    self.t1h = []
                self.xpoints = np.append(self.xpoints, self.x1h[1:])
                self.set_t = np.append(self.set_t, self.t1h[1:])
                self.total_time = self.total_time + time_remaining
            else:
                self.t1h = [self.step1['T']]
        if self.laststep > 1:
            time_remaining = self.step2['Rt']
            if seg < 3:
                self.x2r = np.linspace(
                    self.total_time, self.total_time + self.step2['Rt'], self.npoints)
                self.t2r = np.linspace(self.t1h[-1], self.step2['T'], self.npoints)
            elif seg == 3:
                time_remaining = round(float(self.eth.read_param('TS')) / 3600, 6)
                self.x2r = np.linspace(
                    0, time_remaining, self.npoints)
                self.x2r = np.insert(self.x2r, 0, 0)
                self.t2r = np.linspace(self.current_Temp, self.step2['T'], self.npoints)
                self.t2r = np.insert(self.t2r, 0, 0)
            else:
                self.x2r = []
                self.t2r = []
            self.xpoints = np.append(self.xpoints, self.x2r[1:])
            self.set_t = np.append(self.set_t, self.t2r[1:])
            self.total_time = self.total_time + time_remaining
            if self.step2['H'] > 0:
                time_remaining = self.step2['H']
                if seg < 4:
                    self.x2h = np.linspace(
                        self.total_time, self.total_time + self.step2['H'], self.npoints)
                    self.t2h = np.linspace(
                        self.t2r[-1], self.step2['T'], self.npoints)
                elif seg == 4:
                    time_remaining = round(float(self.eth.read_param('TS')) / 3600, 6)
                    self.x2h = np.linspace(
                        0, time_remaining, self.npoints)
                    self.x2h = np.insert(self.x2h, 0, 0)
                    self.t2h = np.linspace(
                        self.step2['T'], self.step2['T'], self.npoints)
                    self.t2h = np.insert(self.t2h, 0, 0)
                else:
                    self.x2h = []
                    self.t2h = []
                self.xpoints = np.append(self.xpoints, self.x2h[1:])
                self.set_t = np.append(self.set_t, self.t2h[1:])
                self.total_time = self.total_time + time_remaining
            else:
                self.t2h = [self.step2['T']]
        if self.laststep > 2:
            time_remaining = self.step3['Rt']
            if seg < 5:
                self.x3r = np.linspace(
                    self.total_time, self.total_time + self.step3['Rt'], self.npoints)
                self.t3r = np.linspace(self.t2h[-1], self.step3['T'], self.npoints)
            elif seg == 5:
                time_remaining = round(float(self.eth.read_param('TS')) / 3600, 6)
                self.x3r = np.linspace(
                    0, time_remaining, self.npoints)
                self.x3r = np.insert(self.x3r, 0, 0)
                self.t3r = np.linspace(self.current_Temp, self.step3['T'], self.npoints)
                self.t3r = np.insert(self.t3r, 0, 0)
            else:
                self.x3r = []
                self.t3r = []
            self.xpoints = np.append(self.xpoints, self.x3r[1:])
            self.set_t = np.append(self.set_t, self.t3r[1:])
            self.total_time = self.total_time + time_remaining
            if self.step3['H'] > 0:
                time_remaining = self.step3['H']
                if seg < 6:
                    self.x3h = np.linspace(
                        self.total_time, self.total_time + self.step3['H'], self.npoints)
                    self.t3h = np.linspace(
                        self.t3r[-1], self.step3['T'], self.npoints)
                elif seg == 6:
                    time_remaining = round(float(self.eth.read_param('TS')) / 3600, 6)
                    self.x3h = np.linspace(
                        0, time_remaining, self.npoints)
                    self.x3h = np.insert(self.x3h, 0, 0)
                    self.t3h = np.linspace(
                        self.step3['T'], self.step3['T'], self.npoints)
                    self.t3h = np.insert(self.t3h, 0, 0)
                else:
                    self.x3h = []
                    self.t3h = []
                self.xpoints = np.append(self.xpoints, self.x3h[1:])
                self.set_t = np.append(self.set_t, self.t3h[1:])
                self.total_time = self.total_time + time_remaining
            else:
                self.t3h = [self.step3['T']]

    @staticmethod
    def isfloat(value):
        try:
            float(value)
            return True
        except ValueError:
            return False

    def store_software_close_event(self):
        t = localtime()
        elapsed_time = strftime("%H:%M:%S", t)
        with open(self.fname, 'a', newline='') as f:
            f.write(f"\n{elapsed_time}, Software closed.")

    def closeEvent(self, event):
        quit_msg = "Are you sure you want to exit the program?"
        reply = QtGui.QMessageBox.question(self, 'Message',
                                           quit_msg, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.Yes:
            try:
                self.store_software_close_event()
                self.eth.s.close()
            except AttributeError:
                pass
            event.accept()
        else:
            event.ignore()


def main():
    app = QtWidgets.QApplication(sys.argv)
    MainWindow()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
