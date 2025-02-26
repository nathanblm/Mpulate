#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import platform
import serial
import rospy
from threading import Lock
from hiwonder_servo_driver.hiwonder_servo_const import *

exception = None
rx_pin = 7
tx_pin = 13


def port_as_write(): return


def port_as_read(): return


def port_init(): return


if 'raspi' in platform.release():
    import RPi.GPIO as GPIO


    def port_as_write_():
        GPIO.output(tx_pin, 1)  # Pull up TX_CON that is GPIO27
        GPIO.output(rx_pin, 0)  # Pull RX_CON low, which is GPIO17


    def port_as_read_():
        GPIO.output(rx_pin, 1)  # Raise RX_CON is GPIO17
        GPIO.output(tx_pin, 0)  # Pull TX_CON low, which is GPIO27


    def port_init_():
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(rx_pin, GPIO.OUT)  # Configure RX_CON, that is, GPIO17 as output
        GPIO.output(rx_pin, 0)
        GPIO.setup(tx_pin, GPIO.OUT)  # Configure TX_CON i.e. GPIO27 as output
        GPIO.output(tx_pin, 1)


    port_as_read = port_as_read_
    port_as_write = port_as_write_
    port_init = port_init_

port_init()
port_as_write()


class servo_state:
    def __init__(self):
        self.start_timestamp = time.time()
        self.end_timestamp = time.time()
        self.speed = 200
        self.goal = 500
        self.estimated_pos = 500


class HiwonderServoIO:
    def __init__(self, port, baudrate):
        """Open the serial port, initialize the parameters"""
        try:
            self.serial_mutex = Lock()
            self.ser = None
            self.ser = serial.Serial(port, baudrate, timeout=0.01)
            self.port_name = port
            self.servos = {1: servo_state(), 2: servo_state(), 3: servo_state(), 4: servo_state(), 5: servo_state(),
                           6: servo_state()}

        except SerialOpenError:
            raise SerialOpenError(port, baudrate)

    def __del__(self):
        self.close()

    def close(self):
        """
        Be nice, close the serial port.
        """
        if self.ser:
            self.ser.flushInput()
            self.ser.flushOutput()
            self.ser.close()

    def __write_serial(self, data):
        port_as_write()
        time.sleep(0.0005)
        # self.ser.flushOutput()
        self.ser.write(data)
        time.sleep(0.00035)

    def __read_response(self, servo_id):
        data = []
        port_as_read()
        self.ser.flushInput()
        rospy.sleep(0.003)
        try:
            data.extend(self.ser.read(4))
            # print(data)
            if not data[0:2] == [0x55, 0x55]:
                raise Exception('Wrong packet prefix' + str(data[0:2]))
            data.extend(self.ser.read(data[3] - 1))
        except Exception as e:
            raise DroppedPacketError('Invalid response received from servo ' + str(servo_id) + ' ' + str(e))
        finally:
            port_as_write()

        # verify checksum
        checksum = 255 - (sum(data[2: -1]) % 256)
        if not checksum == data[-1]:
            raise ChecksumError(servo_id, data, checksum)
        return data

    def read(self, servo_id, cmd):
        # Number of bytes following standard header (0xFF, 0xFF, id, length)
        length = 3  # instruction, address, size, checksum

        ##Calculate the checksum
        checksum = 255 - ((servo_id + length + cmd) % 256)
        # packet: 0x55  0x55  ID LENGTH INSTRUCTION PARAM_1 ... CHECKSUM
        packet = [0x55, 0x55, servo_id, length, cmd, checksum]

        data = []
        with self.serial_mutex:
            for i in range(2):
                try:
                    self.__write_serial(packet)

                    # wait for response packet from the motor
                    # read response
                    data = self.__read_response(servo_id)
                    timestamp = time.time()
                    data.append(timestamp)
                except Exception as e:
                    if i == 49:
                        raise e

        return data

    def write(self, servo_id, cmd, params):
        """ Write the values from the "data" list to the servo with "servo_id"
        starting with data[0] at "address", continuing through data[n-1] at
        "address" + (n-1), where n = len(data). "address" is an integer between
        0 and 49. It is recommended to use the constants in module dynamixel_const
        for readability. "data" is a list/tuple of integers.
        To set servo with id 1 to position 276, the method should be called
        like:
            write(1, DXL_GOAL_POSITION_L, (20, 1))
        """
        # Number of bytes following standard header (0xFF, 0xFF, id)
        length = 3 + len(params)  # length, cmd, params, checksum

        # Check Sum = ~ ((ID + LENGTH + COMMAND + PARAM_1 + ... + PARAM_N) & 0xFF)
        checksum = 255 - ((servo_id + length + cmd + sum(params)) % 256)

        # packet: FF  FF  ID LENGTH INSTRUCTION PARAM_1 ... CHECKSUM
        packet = [0x55, 0x55, servo_id, length, cmd]
        packet.extend(params)
        packet.append(checksum)
        with self.serial_mutex:
            self.__write_serial(packet)

    def ping(self, servo_id):
        # Number of bytes following standard header (0xFF, 0xFF, id, length)
        length = 3  # instruction, checksum
        checksum = 255 - ((servo_id + length + HIWONDER_SERVO_ID_READ) % 256)
        # packet: 0x55  0x55  ID LENGTH INSTRUCTION CHECKSUM
        packet = [0x55, 0x55, servo_id, length, HIWONDER_SERVO_ID_READ, checksum]

        with self.serial_mutex:
            for i in range(0, 20):
                try:
                    self.__write_serial(packet)
                    response = self.__read_response(servo_id)
                    if response[5] == servo_id:
                        return True
                except Exception as e:
                    response = []
        return False

    def get_position(self, servo_id, fake_read=False):
        if fake_read:
            return self.servos[servo_id].goal
        else:
            response = self.read(servo_id, HIWONDER_SERVO_POS_READ)
            if response:
                self.exception_on_error(response[4], servo_id, 'fetching present position')
                return response[5] + (response[6] << 8)

    def get_voltage(self, servo_id):
        response = self.read(servo_id, HIWONDER_SERVO_VIN_READ)
        if response:
            self.exception_on_error(response[4], servo_id, 'fetching supplied voltage')
            return response[5] + (response[6] << 8)

    def get_feedback(self, servo_id, fake_read=False):
        position = self.get_position(servo_id, fake_read)
        if position:
            time.sleep(0.01)
            goal = self.servos[servo_id].goal
            error = position - goal
            voltage = 9000
            timestamp = time.time()

            return {'timestamp': timestamp,
                    'id': servo_id,
                    'goal': goal,
                    'position': position,
                    'error': error,
                    'voltage': voltage,
                    }
        else:
            return None

    # Servo function operation
    """
    def set_id(oldid, newid):
        Configure the id number of the servo, the factory default is 1
        :param oldid: The original id, the factory default is 1
        :param newid: new id
        serial_serro_wirte_cmd(oldid, HIWONDER_SERVO_ID_WRITE, newid)
    def get_id(id=None):
        Read serial servo id
        :param id: Default is empty
        :return: Return servo id
        while True:
            if id is None:  # There can only be one servo on the bus
                serial_servo_read_cmd(0xfe, HIWONDER_SERVO_ID_READ)
            else:
                serial_servo_read_cmd(id, HIWONDER_SERVO_ID_READ)
            # Obtain content
            msg = serial_servo_get_rmsg(HIWONDER_SERVO_ID_READ)
            if msg is not None:
                return msg
    """

    def set_position(self, servo_id, position, duration=None):
        """
        Drive the serial servo to the specified position
        :param id: Id of the servo to be driven
        :pulse: position
        :use_time: Time required for rotation
        """
        # print("id:{}, pos:{}, duration:{}".format(servo_id, position, duration))
        servo = self.servos[servo_id]

        current_timestamp = time.time()
        if duration is None:
            duration = 20
        servo.goal = int(position)
        duration = 0 if duration < 0 else 30000 if duration > 30000 else duration
        position = 0 if position < 0 else 1000 if position > 1000 else position
        duration = int(duration)
        position = int(position)
        loVal = int(position & 0xFF)
        hiVal = int(position >> 8)
        loTime = int(duration & 0xFF)
        hiTime = int(duration >> 8)
        self.write(servo_id, HIWONDER_SERVO_MOVE_TIME_WRITE, (loVal, hiVal, loTime, hiTime))

    def stop(self, servo_id):
        '''
        Stop the servo
        :param id:
        :return:
        '''
        self.write(servo_id, HIWONDER_SERVO_MOVE_STOP, ())

    """
    def set_deviation(id, d=0):
        adjust the deviation 
        :param id: servo id
        :param d:  deviation 
        serial_serro_wirte_cmd(id, HIWONDER_SERVO_ANGLE_OFFSET_ADJUST, d)

    def save_deviation(id):
        configure deviation，power failure protection
        :param id: servo id
        serial_serro_wirte_cmd(id, HIWONDER_SERVO_ANGLE_OFFSET_WRITE)
        
    def get_dviation(self, servo_id):
        '''
        read deviation
        :param id: servo id
        :return:
        '''
        # Send read deviation command
        count = 0
        while True:
            serial_servo_read_cmd(id, HIWONDER_SERVO_ANGLE_OFFSET_READ)
            # obtain
            msg = serial_servo_get_rmsg(HIWONDER_SERVO_ANGLE_OFFSET_READ)
            count += 1
            if msg is not None:
                return msg
            if count > time_out:
                return None

    def set_angle_limit(id, low, high):
        '''
        set servo rotation range 
        :param id:
        :param low:
        :param high:
        :return:
        '''
        serial_serro_wirte_cmd(id, HIWONDER_SERVO_ANGLE_LIMIT_WRITE, low, high)

    def get_angle_limit(id):
        '''
        read servo rotation range
        :param id:
        :return: return to tuple 0： low  1： high
        '''

        while True:
            serial_servo_read_cmd(id, HIWONDER_SERVO_ANGLE_LIMIT_READ)
            msg = serial_servo_get_rmsg(HIWONDER_SERVO_ANGLE_LIMIT_READ)
            if msg is not None:
                count = 0
                return msg

    def set_vin_limit(self, servo_id, low, high):
        '''
        Set the voltage range of the servo
        :param id:
        :param low:
        :param high:
        :return:
        '''
        serial_serro_wirte_cmd(id, HIWONDER_SERVO_VIN_LIMIT_WRITE, low, high)

    def get_vin_limit(self, servo_id):
        '''
        Read the servo rotation range
        :param id:
        :return: return to tuple 0： low  1： high
        '''
        while True:
            serial_servo_read_cmd(id, HIWONDER_SERVO_VIN_LIMIT_READ)
            msg = serial_servo_get_rmsg(HIWONDER_SERVO_VIN_LIMIT_READ)
            if msg is not None:
                return msg

    def set_temp_limit(id, m_temp):
        '''
        Set the highest temperature alarm of the servo
        :param id:
        :param m_temp:
        :return:
        '''
        serial_serro_wirte_cmd(id, HIWONDER_SERVO_TEMP_MAX_LIMIT_WRITE, m_temp)

    def get_temp_limit(id):
        '''
        Read the temperature alarm range of the servo
        :param id:
        :return:
        '''

        while True:
            serial_servo_read_cmd(id, HIWONDER_SERVO_TEMP_MAX_LIMIT_READ)
            msg = serial_servo_get_rmsg(HIWONDER_SERVO_TEMP_MAX_LIMIT_READ)
            if msg is not None:
                return msg

    def get_position(self, servo_id):
        '''
        read the surrent position of the servo 
        :param id:
        :return:
        '''
        while True:
            serial_servo_read_cmd(id, HIWONDER_SERVO_POS_READ)
            msg = serial_servo_get_rmsg(HIWONDER_SERVO_POS_READ)
            if msg is not None:
                return msg

    def get_temp_current(id):
        '''
        Read the servo temperature
        :param id:
        :return:
        '''
        while True:
            serial_servo_read_cmd(id, HIWONDER_SERVO_TEMP_READ)
            msg = serial_servo_get_rmsg(HIWONDER_SERVO_TEMP_READ)
            if msg is not None:
                return msg

    def get_vin(id):
        '''
        Read servo voltage
        :param id:
        :return:
        '''
        for i in range(0, 10):
            serial_servo_read_cmd(id, HIWONDER_SERVO_VIN_READ)
            msg = serial_servo_get_rmsg(HIWONDER_SERVO_VIN_READ)
            if msg is not None:
                return msg

    def reset(self, servo_id):
        # Servo clear deviation and midpoint of P value（500）
        serial_servo_set_deviation(oldid, 0)    # Clear deviation
        time.sleep(0.1)
        serial_serro_wirte_cmd(oldid, HIWONDER_SERVO_MOVE_TIME_WRITE, 500, 100)    # mid point

    ##power down
    def unload(id):
        serial_serro_wirte_cmd(id, HIWONDER_SERVO_LOAD_OR_UNLOAD_WRITE, 0)

    ##Read whether the power is down
    def get_load_state(id):
        while True:
            serial_servo_read_cmd(id, HIWONDER_SERVO_LOAD_OR_UNLOAD_READ)
            msg = serial_servo_get_rmsg(HIWONDER_SERVO_LOAD_OR_UNLOAD_READ)
            if msg is not None:
                return msg

    """

    def exception_on_error(self, error_code, servo_id, command_failed):
        global exception
        exception = None
        ex_message = '[servo #%d on %s@%sbps]: %s failed' % (servo_id, self.ser.port, self.ser.baudrate, command_failed)

        if not isinstance(error_code, int):
            msg = 'Communcation Error ' + ex_message
            exception = NonfatalErrorCodeError(msg, 0)
            return


class SerialOpenError(Exception):
    def __init__(self, port, baud):
        Exception.__init__(self)
        self.message = "Cannot open port '%s' at %d bps" % (port, baud)
        self.port = port
        self.baud = baud

    def __str__(self):
        return self.message


class ChecksumError(Exception):
    def __init__(self, servo_id, response, checksum):
        Exception.__init__(self)
        self.message = 'Checksum received from motor %d does not match the expected one (%d != %d)' \
                       % (servo_id, response[-1], checksum)
        self.response_data = response
        self.expected_checksum = checksum

    def __str__(self):
        return self.message


class FatalErrorCodeError(Exception):
    def __init__(self, message, ec_const):
        Exception.__init__(self)
        self.message = message
        self.error_code = ec_const

    def __str__(self):
        return self.message


class NonfatalErrorCodeError(Exception):
    def __init__(self, message, ec_const):
        Exception.__init__(self)
        self.message = message
        self.error_code = ec_const

    def __str__(self):
        return self.message


class ErrorCodeError(Exception):
    def __init__(self, message, ec_const):
        Exception.__init__(self)
        self.message = message
        self.error_code = ec_const

    def __str__(self):
        return self.message


class DroppedPacketError(Exception):
    def __init__(self, message):
        Exception.__init__(self)
        self.message = message

    def __str__(self):
        return self.message


class UnsupportedFeatureError(Exception):
    def __init__(self, model_id, feature_id):
        Exception.__init__(self)
        if model_id in HIWONDER_SERVO_PARAMS:
            model = HIWONDER_SERVO_PARAMS[model_id]['name']
        else:
            model = 'Unknown'
        self.message = "Feature %d not supported by model %d (%s)" % (feature_id, model_id, model)

    def __str__(self):
        return self.message
