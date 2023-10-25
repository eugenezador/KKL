

import serial, time

SERIALPORT = "/dev/ttyUSB0"
BAUDRATE = 115200

try:
    ser = serial.Serial(SERIALPORT, BAUDRATE)
except FileNotFoundError as e:
    print ("FILE NOT FOUND")


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

print ('Starting Up Serial Monitor')
ser.close()

try:
    ser.open()

except Exception as e:
    print ("error open serial port: " + str(e))
 #   exit()

if ser.isOpen():

    try:
        ser.flushInput() #flush input buffer, discarding all its contents
        ser.flushOutput()#flush output buffer, aborting current output

        ser.write(b"ps\r")
        print("write data: enable")
        time.sleep(0.5)
        numberOfLine = 0

        while True:

            
            response = ser.readline().decode('ascii', errors='ignore')
            print("read data: " + response)

            numberOfLine = numberOfLine + 1
            if (numberOfLine >= 25):
                break
            #if (response == ''):
                #break

        ser.close()

    except Exception as e:
        print ("error communicating...: " + str(e))

else:
    print ("cannot open serial port ")
