#Based on https://github.com/NickWaterton/Roomba980-Python
import paho.mqtt.client as mqtt
from roomba import Roomba
import argparse
import time
import json
import sys

################################################################################################################################
# MQTT CALLBACK FUNCTIONS
################################################################################################################################
def broker_on_connect(client, userdata, flags, rc):
    print("Broker Connected with result code " + str(rc))
    #subscribe to roomba feedback
    if rc == 0:
        mqttc.subscribe(brokerCommand)
        mqttc.subscribe(brokerSetting)

def broker_on_message(mosq, obj, msg):
    #publish to roomba
    if "command" in msg.topic:
        if args.debug>=3: print("Received COMMAND: %s" % msg.payload.decode('utf-8'))
        myroomba.send_command(msg.payload.decode('utf-8'))
    elif "setting" in msg.topic:
        if args.debug>=3: print("Received SETTING: %s" % str(msg.payload))
        cmd = str(msg.payload).split()
        myroomba.set_preference(cmd[0].payload.decode('utf-8'), cmd[1].payload.decode('utf-8'))

def broker_on_publish(mosq, obj, mid):
    pass

def broker_on_subscribe(mosq, obj, mid, granted_qos):
    if args.debug>=3: print("Broker Subscribed: %s %s" % (str(mid), str(granted_qos)))

def broker_on_disconnect(mosq, obj, rc):
    if args.debug>=3: print("Broker disconnected")

def broker_on_log(mosq, obj, level, string):
    if args.debug>=3: print(string)

################################################################################################################################
# MAIN LOOP
################################################################################################################################
if __name__ == "__main__":
    #parse arguments
    parser = argparse.ArgumentParser('This is an mqtt client for the Roomba.')
    parser.add_argument("-D", "--debug", help="Show debug information on the console (higher value gives more output; max 3)", nargs='?', const=1, type=int, default=0)
    args = parser.parse_args()

    #mqtt broker settings
    broker = 'localhost'
    brokerCommand = "/roomba/command"
    brokerSetting = "/roomba/setting"
    brokerFeedback = "/roomba/feedback"

    #connect to broker
    mqttc = None
    mqttc = mqtt.Client()

    #assign event callbacks
    mqttc.on_message = broker_on_message
    mqttc.on_connect = broker_on_connect
    mqttc.on_disconnect = broker_on_disconnect
    mqttc.on_publish = broker_on_publish
    mqttc.on_subscribe = broker_on_subscribe

    #connect to mqtt broker
    try:
        #mqttc.username_pw_set(user, password)   #put your own mqtt user and password here if you are using them, otherwise comment out
        mqttc.connect(broker, 1883, 60)          #Ping MQTT broker every 60 seconds if no data is published from this script.
    except Exception as e:
        print("Unable to connect to MQTT Broker: %s" % e)
        mqttc = None

    #Roomba connect
    myroomba = Roomba(file='/home/pi/domoticz/plugins/Roomba/config.ini')
    myroomba.set_mqtt_client(mqttc, brokerFeedback) 
    myroomba.connect()

    #start serving forever
    print("<CTRL C> to exit")
    print("Subscribe to /roomba/feedback/# to see published data")

    try:
        if mqttc is not None:
            mqttc.loop_forever()
    except (KeyboardInterrupt, SystemExit):
        print("System exit Received - Exiting program")
        myroomba.disconnect()
        if mqttc is not None:
            mqttc.disconnect()
        sys.exit()
          
