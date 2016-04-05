#!/usr/bin/python

import RPi.GPIO as GPIO
import time
import sys
import urllib

GPIO.setmode(GPIO.BCM)

#GeneralVariables
TimeToSleepAfterTRIGFalse = .55
TriggerDuration = 0.00001
TotalDistance = 0
MaxDistance = 0
MinDistance = 100000
SpeedOfSound = 34029
DataLogFileName = "/home/pi/cistern/DataLogFile"
ProgramLogFileName = "/home/pi/cistern/ProgramLogFile"
GooglePostSuccess = "Data appended successfully."

#Get command line parameters
SensorNumber = int(sys.argv[1])
NumberOfSamples = int(sys.argv[2])
TestMode = int(sys.argv[3])

#Measurment adjustment after real world measurements are taken
Sensor1DistanceOffset = 0
Sensor2DistanceOffset = 0

#Define GPIO pins for sensor relays and delay after powering relays
Sensor1SwitchPin = 5
Sensor2SwitchPin = 6
TimeToSleepAfterPoweringSensor = .5

if SensorNumber == 1:
 TRIG = 23
 ECHO = 12
 DistanceOffset = Sensor1DistanceOffset
#end if

if SensorNumber == 2:
 TRIG = 24
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
SensorHeight = 289.56

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

if SensorNumber == 2:
 #Need to turn off relays if the sensor is #2
 GPIO.output(Sensor1SwitchPin,GPIO.HIGH)
 GPIO.output(Sensor2SwitchPin,GPIO.HIGH)
 if TestMode == 1:
  print "Both relays off."
 time.sleep(1)
#end if
GPIO.cleanup()

if TestMode == 1:
 print "Subtracting Min:",MinDistance,"and Max:",MaxDistance

TotalDistance = TotalDistance - (MinDistance + MaxDistance)
AverageDistance = round(TotalDistance/NumberOfSamples,2)

WaterHeight = SensorHeight - AverageDistance
Gallons = round(WaterHeight*GallonsPerCentimeter,1)
if TestMode == 1:
 print "Avg Distance:",AverageDistance
 print "Water Height:",WaterHeight,"Gallons:",Gallons
 print "URL:",SheetURL

SheetURL = SheetURL + "&SensorHeight=" + str(SensorHeight) + "&WaterHeight=" + str(WaterHeight) + "&Gallons=" + str(Gallons) + "&DistanceToWater=" + str(AverageDistance) + "&MeasurementsTaken=" + str(NumberOfSamples) + "&SensorNumber=" + str(SensorNumber)

DataLogFileEntry = TimeStampDate + " " + TimeStampTime + "," + str(SensorHeight) + "," + str(WaterHeight) + "," + str(NumberOfSamples) + "," + str(AverageDistance) + "," + str(Gallons) + "\n"
DataLogFile = open (DataLogFileName,"a")
DataLogFile.write(DataLogFileEntry)
DataLogFile.close()

Response = urllib.urlopen(SheetURL).read()

if Response == GooglePostSuccess:
 ProgramLogFile.write(time.asctime() + " Google Post Succeeded-> " + SheetURL + "\n")

ThingSpeakURL = ThingSpeakURL + str(Gallons)
ThingSpeakResponse = urllib.urlopen(ThingSpeakURL).read()


ProgramLogFile.write (time.asctime() + " ----- Program complete.-----\n")
ProgramLogFile.close()
