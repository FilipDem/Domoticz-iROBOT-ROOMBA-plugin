# Based on https://github.com/emontnemery/domoticz_mqtt_discovery
import Domoticz
import time


class MqttClient:
    Address = ""
    Port = ""
    mqttConn = None
    isConnected = False
    mqttConnectedCb = None
    mqttDisconnectedCb = None
    mqttPublishCb = None

    def __init__(self, destination, port, mqttConnectedCb, mqttDisconnectedCb, mqttPublishCb, mqttSubackCb):
        Domoticz.Debug("MqttClient::__init__")
        self.Address = destination
        self.Port = port
        self.mqttConnectedCb = mqttConnectedCb
        self.mqttDisconnectedCb = mqttDisconnectedCb
        self.mqttPublishCb = mqttPublishCb
        self.mqttSubackCb = mqttSubackCb
        self.Open()

    def __str__(self):
        Domoticz.Debug("MqttClient::__str__")
        if (self.mqttConn != None):
            return str(self.mqttConn)
        else:
            return "None"

    def Open(self):
        Domoticz.Debug("MqttClient::Open")
        if (self.mqttConn != None):
            self.Close()
        self.isConnected = False
        try:
            self.mqttConn = Domoticz.Connection(Name=self.Address, Transport="TCP/IP", Protocol="MQTT", Address=self.Address, Port=self.Port)
            self.mqttConn.Connect(Timeout=30000)
        except:
            Domoticz.Debug("Problem connecting to MQTT broker.")
            self.mqttConn = None

    def Connect(self):
        Domoticz.Debug("MqttClient::Connect")
        if (self.mqttConn == None):
            self.Open()
        elif self.mqttConn.Connected():
            ID = 'Domoticz_'+str(int(time.time()))
            Domoticz.Log("MQTT CONNECT ID: '" + ID + "'")
            try:
                self.mqttConn.Send({'Verb': 'CONNECT', 'ID': ID})
            except:
                Domoticz.Debug("Problem sending CONNECT message to MQTT broker.")

    def Ping(self):
        Domoticz.Debug("MqttClient::Ping")
        if (self.mqttConn == None or not self.isConnected):
            self.Open()
        elif self.isConnected:
            try:
                self.mqttConn.Send({'Verb': 'PING'})
            except:
                Domoticz.Debug("Problem sending PING message to MQTT broker.")

    def Publish(self, topic, payload, retain = 0):
        Domoticz.Debug("MqttClient::Publish " + topic + " (" + payload + ")")
        if (self.mqttConn == None or not self.isConnected):
            self.Open()
        elif self.isConnected:
            try:
                self.mqttConn.Send({'Verb': 'PUBLISH', 'Topic': topic, 'Payload': bytearray(payload, 'utf-8'), 'Retain': retain})
            except:
                Domoticz.Debug("Problem sending PUBLISH message to MQTT broker.")

    def Subscribe(self, topics):
        Domoticz.Debug("MqttClient::Subscribe")
        subscriptionlist = []
        for topic in topics:
            subscriptionlist.append({'Topic':topic, 'QoS':0})
        if (self.mqttConn == None or not self.isConnected):
            self.Open()
        elif self.isConnected:
            try:
                self.mqttConn.Send({'Verb': 'SUBSCRIBE', 'Topics': subscriptionlist})
            except:
                Domoticz.Debug("Problem sending SUBSCRIBE message to MQTT broker.")

    def Close(self):
        Domoticz.Log("MqttClient::Close")
        self.mqttConn = None
        self.isConnected = False

    def onTimeout(self, Connection):
        Domoticz.Debug("MqttClient::onTimeout")
        self.mqttConn = None

    def onConnect(self, Connection, Status, Description):
        Domoticz.Debug("MqttClient::onConnect")
        if (Status == 0):
            Domoticz.Debug("Successful connect to: "+Connection.Address+":"+Connection.Port)
            self.Connect()
        else:
            Domoticz.Debug("Failed to connect to: "+Connection.Address+":"+Connection.Port+", Description: "+Description)

    def onDisconnect(self, Connection):
        Domoticz.Log("MqttClient::onDisonnect Disconnected from: "+Connection.Address+":"+Connection.Port)
        self.Close()
        # TODO: Reconnect?
        if self.mqttDisconnectedCb != None:
            self.mqttDisconnectedCb()

    def onMessage(self, Connection, Data):
        topic = ''
        if 'Topic' in Data:
            topic = Data['Topic']
        payloadStr = ''
        if 'Payload' in Data:
            payloadStr = Data['Payload'].decode('utf8','replace')
            payloadStr = str(payloadStr.encode('unicode_escape'))

        if Data['Verb'] == "CONNACK":
            self.isConnected = True
            if self.mqttConnectedCb != None:
                self.mqttConnectedCb()

        if Data['Verb'] == "SUBACK":
            if self.mqttSubackCb != None:
                self.mqttSubackCb()

        if Data['Verb'] == "PUBLISH":
            if self.mqttPublishCb != None:
                self.mqttPublishCb(topic, Data['Payload'])
