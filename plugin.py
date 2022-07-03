#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ROOMBA Python Plugin
#
# Author: Filip Demaertelaere
#
# Plugin to manage from Roomba vaccum cleaner from iRobot.
#
"""
<plugin key="Roomba" name="Roomba" author="Filip Demaertelaere" version="1.1.0">
    <description>
      Simple plugin to manage the Roomba from iRobot.
      <br/>
    </description>
    <params>
        <param field="Address" label="MQTT Server address" width="300px" required="true" default="127.0.0.1"/>
        <param field="Port" label="Port" width="300px" required="true" default="1883"/>
        <param field="Username" label="MQTT Username (optional)" width="300px" required="false" default=""/>
        <param field="Password" label="MQTT Password (optional)" width="300px" required="false" default="" password="true"/>
        <param field="Mode5" label="Timeout (minutes)" width="120px" required="true" default="15"/>
        <param field="Mode6" label="Debug" width="120px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal" default="true"/>
            </options>
        </param>
     </params>
</plugin>
"""
import Domoticz
from mqtt import MqttClient
from roomba import Roomba
from datetime import datetime
import json

#DEFAULT IMAGE
_IMAGE_ROOMBA = "Roomba"

#DEVICES TO CREATE
_UNIT_STATE = 1
_UNIT_RUNNING = 2
_UNIT_BAT = 3

#VALUE TO INDICATE THAT THE DEVICE TIMED-OUT
_TIMEDOUT = 1

#DEBUG
_DEBUG_OFF = 0
_DEBUG_ON = 2

#ROOMBA SPECIFIC
_COMMANDS = '/roomba/command'
_FEEDBACK = '/roomba/feedback'
_STATE = '/roomba/feedback/Roomba/state'
_BATPCT = '/roomba/feedback/Roomba/batPct'
_START = 'start'
_STOP = 'stop'
_DOCK = 'dock'

class BasePlugin:

    HEARTBEAT_SEC = 10

    def __init__(self):
        self.mqttClient = None
        self.myroomba = None
        self.state = None
        self.batpct = None
        self.execute = None
        self.MqttUpdatereceived = False
        self.lastMqttUpdate = datetime.now()
        return

    def onStart(self):

        # Debugging On/Off
        self.debug = _DEBUG_ON if Parameters["Mode6"] == "Debug" else _DEBUG_OFF
        Domoticz.Debugging(self.debug)

        # Create images if necessary
        if _IMAGE_ROOMBA not in Images:
            Domoticz.Image("Roomba.zip").Create()

        # Create devices (USED BY DEFAULT)
        CreateDevicesUsed()
        TimeoutDevice(All=True)

        # Create devices (NOT USED BY DEFAULT)
        CreateDevicesNotUsed()

        # Global settings
        DumpConfigToLog()

        # Start MQTT
        try:
            mqtt_server_address = Parameters["Address"].strip()
            mqtt_server_port = Parameters["Port"].strip()
            self.mqttClient = MqttClient(mqtt_server_address, mqtt_server_port, self.onMQTTConnected, self.onMQTTDisconnected, self.onMQTTPublish, self.onMQTTSubscribed)
        except Exception as e:
            Domoticz.Error("MQTT client start error: "+str(e))
            self.mqttClient = None

    def onStop(self):
        Domoticz.Debug("onStop called")

    def onCommand(self, Unit, Command, Level, Color):  # react to commands arrived from Domoticz
        Domoticz.Debug("Command: " + Command + " (" + str(Level) + ") Color:" + Color)
        if Unit == _UNIT_RUNNING:
            if Command == 'On':
                if self.state == 'Charging':
                    self.mqttClient.Publish(_COMMANDS, 'start')
                else:
                    self.mqttClient.Publish(_COMMANDS, 'dock')
            else:
                self.mqttClient.Publish(_COMMANDS, 'stop')
                self.execute = _DOCK

    def onConnect(self, Connection, Status, Description):
        Domoticz.Debug("Connection: " + str(Status))
        if self.mqttClient is not None:
            self.mqttClient.onConnect(Connection, Status, Description)

    def onDisconnect(self, Connection):
        if self.mqttClient is not None:
            self.mqttClient.onDisconnect(Connection)

    def onMessage(self, Connection, Data):
        if self.mqttClient is not None:
            self.mqttClient.onMessage(Connection, Data)

    def onHeartbeat(self):
        Domoticz.Debug("Heartbeating...")

        if self.mqttClient is not None:
            try:
                # Reconnect if connection has dropped
                if self.mqttClient.mqttConn is None or (not self.mqttClient.mqttConn.Connecting() and not self.mqttClient.mqttConn.Connected() or not self.mqttClient.isConnected):
                    Domoticz.Debug("Reconnecting")
                    self.mqttClient.Open()
                else:
                    self.mqttClient.Ping()

                    # Commands to Roomba
                    if self.execute == _DOCK:
                        if self.state == 'Stopped':
                            self.mqttClient.Publish(_COMMANDS, 'dock')
                        if self.state == 'Charging':
                            self.execute = None
                
            except Exception as e:
                Domoticz.Error("onHeartbeat: " + str(e))
                
         # Update devices
        if self.MqttUpdatereceived:
            if self.state:
                UpdateDevice(_UNIT_STATE, 0, self.state, Images[_IMAGE_ROOMBA].ID)
                if self.state == 'Running':
                    UpdateDevice(_UNIT_RUNNING, 1, 1, Images[_IMAGE_ROOMBA].ID)
                else:
                    UpdateDevice(_UNIT_RUNNING, 0, 0, Images[_IMAGE_ROOMBA].ID)
            if self.batpct:
                UpdateDeviceBatSig(_UNIT_RUNNING, self.batpct)
                UpdateDevice(_UNIT_BAT, self.batpct, self.batpct, Images[_IMAGE_ROOMBA].ID)
            self.MqttUpdatereceived = False
            
        # Check if getting information from MQTT Broker
        if (datetime.now()-self.lastMqttUpdate).total_seconds() > int(Parameters["Mode5"]) * 60:
            TimeoutDevice(All=True)

    def onMQTTConnected(self):
        Domoticz.Debug("onMQTTConnected")
        if self.mqttClient is not None:
            self.mqttClient.Subscribe([_STATE, _BATPCT])

    def onMQTTDisconnected(self):
        Domoticz.Debug("onMQTTDisconnected")

    def onMQTTSubscribed(self):
        Domoticz.Debug("onMQTTSubscribed")

    def onMQTTPublish(self, topic, message): # process incoming MQTT statuses
        message = message.decode('utf-8')
        Domoticz.Debug("MQTT message: " + topic + " " + message)
        if topic == _STATE:
            self.state = message
            self.lastMqttUpdate = datetime.now()
            self.MqttUpdatereceived = True
        if topic == _BATPCT:
            self.batpct = int(message)
            self.lastMqttUpdate = datetime.now()
            self.MqttUpdatereceived = True

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onDeviceModified(Unit):
    global _plugin
    return

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Color):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Color)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()
    
################################################################################
# Generic helper functions
################################################################################

#DUMP THE PARAMETER
def DumpConfigToLog():
    for parameter in Parameters:
        if Parameters[parameter] != "":
            Domoticz.Debug("> Parameter {}: {}".format(parameter, Parameters[parameter]))
    Domoticz.Debug("> Got {} devices:".format(len(Devices)))
    for device in Devices:
        Domoticz.Debug("> Device {} {}".format(device, Devices[device]))
        Domoticz.Debug("> Device {} DeviceID:    {}".format(device, Devices[device].DeviceID))
        Domoticz.Debug("> Device {} Description: {}".format(device, Devices[device].Description))
        Domoticz.Debug("> Device {} LastLevel:   {}".format(device, Devices[device].LastLevel))

#UPDATE THE DEVICE
def UpdateDevice(Unit, nValue, sValue, Image, TimedOut=0, AlwaysUpdate=False):
    if Unit in Devices:
        if Devices[Unit].nValue != int(nValue) or Devices[Unit].sValue != str(sValue) or Devices[Unit].TimedOut != TimedOut or Devices[Unit].Image != Image or AlwaysUpdate:
            Devices[Unit].Update(nValue=int(nValue), sValue=str(sValue), Image=Image, TimedOut=TimedOut)
            Domoticz.Debug("Update " + Devices[Unit].Name + ": " + str(nValue) + " - '" + str(sValue) + "'")
        else:
            if not TimedOut:
                Devices[Unit].Touch()

#UPDATE THE BATTERY LEVEL AND SIGNAL STRENGTH OF A DEVICE
def UpdateDeviceBatSig(Unit, BatteryLevel=255, SignalLevel=12):
    if Unit in Devices:
        if Devices[Unit].BatteryLevel != int(BatteryLevel) or Devices[Unit].SignalLevel != int(SignalLevel):
            Domoticz.Debug("Going to Update " + Devices[Unit].Name + ": " + str(Devices[Unit].nValue) + " - '" + str(Devices[Unit].sValue) + "' - " + str(BatteryLevel) + " - " + str(SignalLevel))
            Devices[Unit].Update(nValue=Devices[Unit].nValue, sValue=Devices[Unit].sValue, BatteryLevel=int(BatteryLevel), SignalLevel=int(SignalLevel))
            Domoticz.Debug("Updated " + Devices[Unit].Name + ": " + str(Devices[Unit].nValue) + " - '" + str(Devices[Unit].sValue) + "' - " + str(BatteryLevel) + " - " + str(SignalLevel))

#SET DEVICE ON TIMED-OUT (OR ALL DEVICES)
def TimeoutDevice(All, Unit=0):
    if All:
        for x in Devices:
            UpdateDevice(x, Devices[x].nValue, Devices[x].sValue, Devices[x].Image, TimedOut=_TIMEDOUT)
    else:
        UpdateDevice(Unit, Devices[Unit].nValue, Devices[Unit].sValue, Devices[Unit].Image, TimedOut=_TIMEDOUT)

#CREATE ALL THE DEVICES (USED)
def CreateDevicesUsed():
    if (_UNIT_STATE not in Devices):
        Domoticz.Device(Name="State", Unit=_UNIT_STATE, TypeName="Text", Image=Images[_IMAGE_ROOMBA].ID, Used=1).Create()
    if (_UNIT_RUNNING not in Devices):
        Domoticz.Device(Unit=_UNIT_RUNNING, Name="Run", Type=244, Subtype=73, Switchtype=0, Image=Images[_IMAGE_ROOMBA].ID, Used=1).Create()

#CREATE ALL THE DEVICES (NOT USED)
def CreateDevicesNotUsed():
    if (_UNIT_BAT not in Devices):
        Domoticz.Device(Unit=_UNIT_BAT, Name="Battery Level", TypeName="Custom", Options={"Custom": "0;%"}, Image=Images[_IMAGE_ROOMBA].ID, Used=0).Create()
