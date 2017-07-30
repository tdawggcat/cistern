#!/usr/bin/python

import RPi.GPIO as GPIO
import os
import glob
import time
import sys
import urllib

# Global definitions and system calls
GPIO.setmode(GPIO.BCM)
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

############################################################################
#GeneralVariables
TempFileBrownCisternAir = '/sys/bus/w1/devices/28-800000081184/w1_slave'
TempFileOrangeOutsideAir = '/sys/bus/w1/devices/28-00152c26fdee/w1_slave'
TempFileGreenOutsideOnCistern = '/sys/bus/w1/devices/28-0315a4acc8ff/w1_slave'
TempFileBlueWater = '/sys/bus/w1/devices/28-00152335c4ee/w1_slave'
MaxTempTests = 5

TimeToSleepAfterTRIGFalse = .65
TriggerDuration = 0.00001
TotalDistance = 0
MaxDistance = 0
MinDistance = 100000
#SpeedOfSound = 34029
#Speed of sound adjusted to cistern elevation per https://www.daftlogic.com/sandbox-google-maps-find-altitude.htm
SpeedOfSound = 33900
DataLogFileName = "/home/pi/cistern/DataLogFile"
ProgramLogFileName = "/home/pi/cistern/ProgramLogFile"
GooglePostSuccess = "Data appended successfully."

#Measurment adjustment after real world measurements are taken
Sensor1DistanceOffset = 0.86
Sensor2DistanceOffset = 0.94

#Get command line parameters
SensorNumber = int(sys.argv[1])
NumberOfSamples = int(sys.argv[2])
TestMode = int(sys.argv[3])

#Define GPIO pins for sensor relays and delay after powering relays
Sensor1SwitchPin = 5
Sensor2SwitchPin = 6
TimeToSleepAfterPoweringSensor = .5
# 28 Jul 2017 - Both sensors use the same trigger
TRIG = 23

# End Variables section
############################################################################

#Function to test for valid temperature
def funValidTemp(TestTemp):
# 30 July 2017 - Appears sometimes the probe returns a flat max of 185 deg F.
# print "TestTemp: ", TestTemp
 if TestTemp == 185.0:
  return 0
 # End if
 # If all tests pass we'll end up here, return as a valid temp
 return 1
# End function

#Function for reading the temperature files
def read_temp(DeviceFile):
    f = open(DeviceFile, 'r')
    lines = f.readlines()
    f.close()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        temp_f = round((temp_c * 9.0 / 5.0 + 32.0),1)
        return temp_f
#End Temperature function

def funGetTemp(SensorDeviceFile):
#Set to 0 to force into the loop
 ValidTemp = 0
 NumTests = 0

 while (ValidTemp != 1) and (NumTests < MaxTempTests):
  NumTests = NumTests + 1
#  print "Test ",NumTests
  time.sleep(1)
  SensorTemp = read_temp(SensorDeviceFile)
#  SensorTemp = 185.0
  if funValidTemp(SensorTemp) == 0:
#   print "INVALID TEMP"
   SensorTemp = ""
  else:
   ValidTemp = 1
#   print "VALID TEMP"
# End while
 return SensorTemp
# End Function funGetTemp

time.sleep(1)
BrownCisternAir = funGetTemp(TempFileBrownCisternAir)
time.sleep(1)
OrangeOutsideAir = funGetTemp(TempFileOrangeOutsideAir)
time.sleep(1)
GreenOutsideOnCistern = funGetTemp(TempFileGreenOutsideOnCistern)
time.sleep(1)
BlueWater = funGetTemp(TempFileBlueWater)

if TestMode == 1:
 print "Cistern Air        : ",BrownCisternAir
 print "Outside Air        : ",OrangeOutsideAir
 print "Outside On Cistern : ",GreenOutsideOnCistern
 print "Water              : ",BlueWater
#end if


if SensorNumber == 1:
 ECHO = 12
 DistanceOffset = Sensor1DistanceOffset
#end if

if SensorNumber == 2:
 ECHO = 20
 DistanceOffset = Sensor2DistanceOffset

 # If sensor is 1, switches stay put. If 2, swap them
 # LOW is on, HIGH is off
 GPIO.setup(Sensor1SwitchPin,GPIO.OUT)
 GPIO.setup(Sensor2SwitchPin,GPIO.OUT)
 GPIO.output(Sensor1SwitchPin,GPIO.LOW)
 GPIO.output(Sensor2SwitchPin,GPIO.LOW)
 time.sleep(TimeToSleepAfterPoweringSensor)
#end if



#Mounting height of sensor (cm)
#SensorHeight = 289.56
SensorHeight = 289.24

#Gallons per cm, based on 5000 gallons per foot
GallonsPerCentimeter = 164.04

TimeStampDate = time.strftime('%m/%d/%Y')
TimeStampTime = time.strftime('%H:%M:%S')

SheetURL = "https://script.google.com/macros/s/AKfycbxuZ1cDvcRTCCpcNL2xyDH3btD-MQMYFO7vtxrUqhxwuGmeWkn7/exec?TimeStamp="+TimeStampDate+"%20"+TimeStampTime
ThingSpeakURL = "https://api.thingspeak.com/update?api_key=QMENBYAFGG5QXLJK&field1="

ProgramLogFile = open(ProgramLogFileName,"a")
ProgramLogFile.write (time.asctime() + " -----Program starting-----\n")
ProgramLogFile.write (time.asctime() + " Beginning " + str(NumberOfSamples+2) + " total measurements.\n")

if TestMode == 1:
 print "Taking",NumberOfSamples,"samples."
for x in range (1,NumberOfSamples+3):
# Begin loop
 GPIO.setup(TRIG,GPIO.OUT)
 GPIO.setup(ECHO,GPIO.IN)
 GPIO.output(TRIG, False)
 time.sleep(TimeToSleepAfterTRIGFalse)
 GPIO.output(TRIG, True)
 time.sleep(TriggerDuration)
 GPIO.output(TRIG, False)

 while GPIO.input(ECHO)==0:
  PulseStart = time.time()

 while GPIO.input(ECHO)==1:
  PulseEnd = time.time()
 
 PulseDuration = PulseEnd - PulseStart

 Distance = round((PulseDuration * (SpeedOfSound / 2)) + DistanceOffset, 2)

 TotalDistance = TotalDistance + Distance
 if Distance > MaxDistance:
  MaxDistance = Distance

 if Distance < MinDistance:
  MinDistance = Distance

 if TestMode == 1:
  print x,"- Distance:",Distance,"cm Total:",TotalDistance,"cm Max:",MaxDistance,"cm Min:",MinDistance,"cm"
# End loop

ProgramLogFile.write (time.asctime() + " Measurements complete.\n")

if SensorNumber == 2:
 #Need to turn off relays if the sensor is #2
 GPIO.output(Sensor1SwitchPin,GPIO.HIGH)
 GPIO.output(Sensor2SwitchPin,GPIO.HIGH)
 if TestMode == 1:
  print "Both relays off."
 time.sleep(1)
 ProgramLogFile.write (time.asctime() + " Turned sensors off.\n")
#end if
GPIO.cleanup()

if TestMode == 1:
 print "Subtracting Min:",MinDistance,"and Max:",MaxDistance

TotalDistance = TotalDistance - (MinDistance + MaxDistance)
AverageDistance = round(TotalDistance/NumberOfSamples,2)


#BrownCisternAir = read_temp(TempFileBrownCisternAir)
#OrangeOutsideAir = read_temp(TempFileOrangeOutsideAir)
#GreenOutsideOnCistern = read_temp(TempFileGreenOutsideOnCistern)
#BlueWater = read_temp(TempFileBlueWater)


WaterHeight = SensorHeight - AverageDistance
Gallons = round(WaterHeight*GallonsPerCentimeter,1)
SheetURL = SheetURL + "&SensorHeight=" + str(SensorHeight) + "&WaterHeight=" + str(WaterHeight) + "&Gallons=" + str(Gallons) + "&DistanceToWater=" + str(AverageDistance) + "&MeasurementsTaken=" + str(NumberOfSamples) + "&SensorNumber=" + str(SensorNumber) + "&WaterTemp=" + str(BlueWater) + "&CisternAirTemp=" + str(BrownCisternAir) + "&OutsideAirTemp=" + str(OrangeOutsideAir) + "&OutsideCisternSurface=" + str(GreenOutsideOnCistern)
ThingSpeakURL = ThingSpeakURL + str(Gallons) + "&field2=" + str(BlueWater) + "&field3=" + str(BrownCisternAir) + "&field4=" + str(OrangeOutsideAir) + "&field5=" + str(GreenOutsideOnCistern)

ProgramLogFile.write (time.asctime() + " SheetURL:" + SheetURL  + " .\n")
ProgramLogFile.write (time.asctime() + " ThingSpeakURL:" + ThingSpeakURL  + " .\n")


if TestMode == 1:
 print "Avg Distance:",AverageDistance
 print "Water Height:",WaterHeight,"Gallons:",Gallons
 print "GoogleSheetURL:",SheetURL
 print "ThingSpeakURL:",ThingSpeakURL
#end if test mode == 1

if ((TestMode == 0) and (Gallons < 50000)):
 DataLogFileEntry = TimeStampDate + " " + TimeStampTime + "," + str(SensorHeight) + "," + str(WaterHeight) + "," + str(NumberOfSamples) + "," + str(AverageDistance) + "," + str(Gallons) + "," + str(SensorNumber) + "," + str(BlueWater) + "," + str(BrownCisternAir) + "," + str(OrangeOutsideAir) + "," + str(GreenOutsideOnCistern) + "\n"
 DataLogFile = open (DataLogFileName,"a")
 DataLogFile.write(DataLogFileEntry)
 DataLogFile.close()
 Response = urllib.urlopen(SheetURL).read()

 if Response == GooglePostSuccess:
  ProgramLogFile.write(time.asctime() + " Google Post Succeeded-> " + SheetURL + "\n")

 ThingSpeakResponse = urllib.urlopen(ThingSpeakURL).read()
#end if

ProgramLogFile.write (time.asctime() + " ----- Program complete.-----\n")
ProgramLogFile.close()
