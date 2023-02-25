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
<plugin key="Roomba" name="Roomba" author="Filip Demaertelaere" version="1.3.0">
    <description>
        Plugin to manage the Roomba from iRobot.<br/><br/>
    </description>
    <params>
        <param field="Address" label="MQTT Server Address" width="300px" required="true" default="127.0.0.1"/>
        <param field="Port" label="MQTT Server Port" width="300px" required="true" default="1883"/>
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

import sys, os
major,minor,x,y,z = sys.version_info
sys.path.append('/usr/lib/python3/dist-packages')
sys.path.append('/usr/local/lib/python{}.{}/dist-packages'.format(major, minor))
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from domoticz_tools import *
import Domoticz
import configparser
import re
from mqtt import MqttClient
from datetime import datetime
from ast import literal_eval

#DEFAULT IMAGE
_IMAGE_ROOMBA = 'Roomba'

#CONfig FILENAME
CONFIG = 'config.ini'

#DEVICES
STATE = 'State'
RUN = 'Run'
BATTERY = 'Battery Level'
ERROR = 'Error'

#ROOMBA SPECIFIC
_COMMANDS = '/roomba/command/'
_FEEDBACK = '/roomba/feedback/'
_STATE = '/state'
_BATPCT = '/batPct'
_ERROR = '/error_message'
_START = 'start'
_STOP = 'stop'
_DOCK = 'dock'
_CHARGING = 'Charging'
_STOPPED = 'Stopped'

################################################################################
# Start Plugin
################################################################################

class BasePlugin:

    HEARTBEAT_SEC = 10

    def __init__(self):
        self.debug = DEBUG_OFF
        self.runAgain = MINUTE
        self.mqttClient = None
        self.myroombas = {}

    def onStart(self):

        # Debugging On/Off
        self.debug = DEBUG_ON if Parameters['Mode6'] == 'Debug' else DEBUG_OFF
        Domoticz.Debugging(self.debug)
        if self.debug == DEBUG_ON:
            DumpConfigToLog(Parameters, Devices)

        # Create images if necessary
        if _IMAGE_ROOMBA not in Images:
            Domoticz.Image('Roomba.zip').Create()

        # Read config file
        Config = configparser.ConfigParser()
        try:
            Config.read('{}{}'.format(Parameters['HomeFolder'], CONFIG))
            Domoticz.Debug('Reading info from configuration file "{}"'.format(CONFIG))
            self.myroombas = { literal_eval(v).get('robotname'): {} for s in Config.sections() for k, v in Config.items(s) if k == 'data' }
            Domoticz.Debug('Roombas found in configuration file: {}'.format(self.myroombas))
        except:
            Domoticz.Error('Error reading the configuration file {}{}'.format(Parameters['HomeFolder'], CONFIG))
            self.myroombas.clear()

        # Create devices
        for roomba in self.myroombas:
            Unit = FindUnitFromName(Devices, Parameters, '{} - {}'.format(roomba, STATE))
            if not Unit:
                Unit = GetNextFreeUnit(Devices)
                Domoticz.Device(Unit=Unit, Name='{} - {}'.format(roomba, STATE), TypeName='Text', Image=Images[_IMAGE_ROOMBA].ID, Used=1).Create()
            Unit = FindUnitFromName(Devices, Parameters, '{} - {}'.format(roomba, RUN))
            if not Unit:
                Unit = GetNextFreeUnit(Devices)
                Domoticz.Device(Unit=Unit, Name='{} - {}'.format(roomba, RUN), Type=244, Subtype=73, Switchtype=0, Image=Images[_IMAGE_ROOMBA].ID, Used=1).Create()
            Unit = FindUnitFromName(Devices, Parameters, '{} - {}'.format(roomba, BATTERY))
            if not Unit:
                Unit = GetNextFreeUnit(Devices)
                Domoticz.Device(Unit=Unit, Name='{} - {}'.format(roomba, BATTERY), TypeName='Custom', Options={'Custom': '0;%'}, Image=Images[_IMAGE_ROOMBA].ID, Used=0).Create()
            Unit = FindUnitFromName(Devices, Parameters, '{} - {}'.format(roomba, ERROR))
            if not Unit:
                Unit = GetNextFreeUnit(Devices)
                Domoticz.Device(Unit=Unit, Name='{} - {}'.format(roomba, ERROR), TypeName='Text', Image=Images[_IMAGE_ROOMBA].ID, Used=1).Create()
        TimeoutDevice(Devices, All=True)
        
        # Start MQTT
        try:
            mqtt_server_address = Parameters["Address"].strip()
            mqtt_server_port = Parameters["Port"].strip()
            self.mqttClient = MqttClient(mqtt_server_address, mqtt_server_port, self.onMQTTConnected, self.onMQTTDisconnected, self.onMQTTPublish, self.onMQTTSubscribed)
        except Exception as e:
            Domoticz.Error('MQTT client start error: {}'.format(e))
            self.mqttClient = None

    def onStop(self):
        Domoticz.Debug('onStop called')

    def onCommand(self, Unit, Command, Level, Color):  # react to commands arrived from Domoticz
        Domoticz.Debug('onCommand called for "{}" Unit: {} - Parameter: {} - Level: {}'.format(Devices[Unit].Name, Unit, Command, Level))
        if Devices[Unit].Name.endswith(RUN):
            try:
                roomba = re.search('{} - (.*?) - {}'.format(Parameters['Name'], RUN), Devices[Unit].Name)[1]
                Domoticz.Debug('iRobot found to send command to ({}).'.format(roomba))
                if roomba in self.myroombas:
                    if Command == 'On':
                        if self.myroombas[roomba][_STATE[1:]] == _CHARGING:
                            self.mqttClient.Publish('{}{}'.format(_COMMANDS, roomba), _START)
                        else:
                            self.mqttClient.Publish('{}{}'.format(_COMMANDS, roomba), _DOCK)
                    else:
                        self.mqttClient.Publish('{}{}'.format(_COMMANDS, roomba), _STOP)
                        self.myroombas[roomba]['execute'] = _DOCK
                else:
                    Domoticz.Status('"{}" is not a valid iRobot (not found in the file "{}").'.format(roomba, CONFIG))                
            except:
                pass

    def onConnect(self, Connection, Status, Description):
        Domoticz.Debug('Connection: {}'.format(Status))
        if self.mqttClient is not None:
            self.mqttClient.onConnect(Connection, Status, Description)

    def onDisconnect(self, Connection):
        if self.mqttClient is not None:
            self.mqttClient.onDisconnect(Connection)

    def onMessage(self, Connection, Data):
        if self.mqttClient is not None:
            self.mqttClient.onMessage(Connection, Data)
            
    def onTimeout(self, Connection):
        Domoticz.Error("Timeout out on connection received.")
        if self.mqttClient is not None:
            self.mqttClient.onTimeout(Connection)
        self.runAgain = MINUTE

    def onHeartbeat(self):

        if self.mqttClient is not None:
            try:
                # Reconnect if connection has dropped
                if self.mqttClient.mqttConn is None or not (self.mqttClient.mqttConn.Connecting() or (self.mqttClient.mqttConn.Connected() and self.mqttClient.isConnected)):
                    Domoticz.Debug('Reconnecting')
                    self.mqttClient.Open()
                elif self.mqttClient.isConnected:
                    self.mqttClient.Ping()

                    # Commands to Roomba
                    for roomba in self.myroombas:
                        if _STATE[1:] in roomba and 'execute' in roomba and roomba['execute'] == _DOCK:
                            if roomba[_STATE[1:]] == _STOPPED:
                                self.mqttClient.Publish('{}{}'.format(_COMMANDS, roomba), _DOCK)
                            elif roomba[_STATE[1:]] == _CHARGING:
                                roomba['execute'] = ''
                
            except Exception as e:
                Domoticz.Error('General error with Roomba: {}'.format(e))
                
        self.runAgain -= 1
        if self.runAgain <= 0:

            Domoticz.Debug('Heartbeat - Status of all iRobots: {}.'.format(self.myroombas))
            
            # Update devices
            for roomba in self.myroombas:
                if 'MqttUpdatereceived' in self.myroombas[roomba] and self.myroombas[roomba]['MqttUpdatereceived']:
                    if _STATE[1:] in self.myroombas[roomba] and self.myroombas[roomba][_STATE[1:]]:
                        Unit = FindUnitFromName(Devices, Parameters, '{} - {}'.format(roomba, STATE))
                        if not Unit: Unit = FindUnitFromDescription(Devices, Parameters, '{} - {}'.format(roomba, STATE))
                        UpdateDevice(False, Devices, Unit, 0, self.myroombas[roomba][_STATE[1:]])
                        Unit = FindUnitFromName(Devices, Parameters, '{} - {}'.format(roomba, RUN))
                        if not Unit: Unit = FindUnitFromDescription(Devices, Parameters, '{} - {}'.format(roomba, RUN))
                        if self.myroombas[roomba][_STATE[1:]] == 'Running':
                            UpdateDevice(False, Devices, Unit, 1, 1)
                        else:
                            UpdateDevice(False, Devices, Unit, 0, 0)
                            
                    if _BATPCT[1:] in self.myroombas[roomba] and self.myroombas[roomba][_BATPCT[1:]]:
                        Unit = FindUnitFromName(Devices, Parameters, '{} - {}'.format(roomba, RUN))
                        if not Unit: Unit = FindUnitFromDescription(Devices, Parameters, '{} - {}'.format(roomba, RUN))
                        UpdateDeviceBatSig(False, Devices, Unit, BatteryLevel=self.myroombas[roomba][_BATPCT[1:]])
                        Unit = FindUnitFromName(Devices, Parameters, '{} - {}'.format(roomba, BATTERY))
                        if not Unit: Unit = FindUnitFromDescription(Devices, Parameters, '{} - {}'.format(roomba, BATTERY))
                        UpdateDevice(False, Devices, Unit, self.myroombas[roomba][_BATPCT[1:]], self.myroombas[roomba][_BATPCT[1:]])
                        
                    if _ERROR[1:] in self.myroombas[roomba] and self.myroombas[roomba][_ERROR[1:]]:
                        Unit = FindUnitFromName(Devices, Parameters, '{} - {}'.format(roomba, ERROR))
                        if not Unit: Unit = FindUnitFromDescription(Devices, Parameters, '{} - {}'.format(roomba, ERROR))
                        UpdateDevice(False, Devices, Unit, 0, self.myroombas[roomba][_ERROR[1:]])

                    self.myroombas[roomba]['MqttUpdatereceived'] = False
        
            # Check if getting information from MQTT Broker
            for roomba in self.myroombas:
                if 'lastMqttUpdate' in self.myroombas[roomba] and (datetime.now()-self.myroombas[roomba]['lastMqttUpdate']).total_seconds() > int(Parameters['Mode5']) * 60:
                    Unit = FindUnitFromName(Devices, Parameters, '{} - {}'.format(roomba, STATE))
                    if not Unit: Unit = FindUnitFromDescription(Devices, Parameters, '{} - {}'.format(roomba, STATE))
                    TimeoutDevice(Devices, All=False, Unit=Unit)
                    Unit = FindUnitFromName(Devices, Parameters, '{} - {}'.format(roomba, RUN))
                    if not Unit: Unit = FindUnitFromDescription(Devices, Parameters, '{} - {}'.format(roomba, RUN))
                    TimeoutDevice(Devices, All=False, Unit=Unit)
                    Unit = FindUnitFromName(Devices, Parameters, '{} - {}'.format(roomba, BATTERY))
                    if not Unit: Unit = FindUnitFromDescription(Devices, Parameters, '{} - {}'.format(roomba, BATTERY))
                    TimeoutDevice(Devices, All=False, Unit=Unit)
                    Unit = FindUnitFromName(Devices, Parameters, '{} - {}'.format(roomba, ERROR))
                    if not Unit: Unit = FindUnitFromDescription(Devices, Parameters, '{} - {}'.format(roomba, ERROR))
                    TimeoutDevice(Devices, All=False, Unit=Unit)

            self.runAgain = MINUTE
             
    def onMQTTConnected(self):
        Domoticz.Debug('onMQTTConnected')
        if self.mqttClient is not None:
            self.mqttClient.Subscribe([ item for roomba in self.myroombas for item in ['{}{}{}'.format(_FEEDBACK, roomba, _STATE), '{}{}{}'.format(_FEEDBACK, roomba, _BATPCT), '{}{}{}'.format(_FEEDBACK, roomba, _ERROR)] ])

    def onMQTTDisconnected(self):
        Domoticz.Debug('onMQTTDisconnected')

    def onMQTTSubscribed(self):
        Domoticz.Debug('onMQTTSubscribed')

    def onMQTTPublish(self, topic, message): # process incoming MQTT statuses
        message = message.decode('utf-8')
        Domoticz.Debug('MQTT message: {} - {}'.format(topic, message))
        if topic.startswith(_FEEDBACK):
            if topic.endswith(_STATE):
                try:
                    roomba = re.search('{}(.*?){}'.format(_FEEDBACK, _STATE), topic)[1]
                    self.myroombas[roomba][_STATE[1:]] = message
                    self.myroombas[roomba]['lastMqttUpdate'] = datetime.now()
                    self.myroombas[roomba]['MqttUpdatereceived'] = True
                except:
                    pass
            elif topic.endswith(_BATPCT):
                try:
                    roomba = re.search('{}(.*?){}'.format(_FEEDBACK, _BATPCT), topic)[1]
                    self.myroombas[roomba][_BATPCT[1:]] = int(message)
                    self.myroombas[roomba]['lastMqttUpdate'] = datetime.now()
                    self.myroombas[roomba]['MqttUpdatereceived'] = True
                except:
                    pass
            elif topic.endswith(_ERROR):
                try:
                    roomba = re.search('{}(.*?){}'.format(_FEEDBACK, _ERROR), topic)[1]
                    self.myroombas[roomba][_ERROR[1:]] = message
                    self.myroombas[roomba]['lastMqttUpdate'] = datetime.now()
                    self.myroombas[roomba]['MqttUpdatereceived'] = True
                except:
                    pass
        Domoticz.Debug('MQTT Published - Status of all iRobots: {}.'.format(self.myroombas))

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
# Specific helper functions
################################################################################
