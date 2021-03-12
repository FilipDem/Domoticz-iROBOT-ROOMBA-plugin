# Donation
It took me quite some effort to get the plugin available. Small contributions are welcome...

## Use your Mobile Banking App and scan the QR Code
The QR codes comply the EPC069-12 European Standard for SEPA Credit Transfers ([SCT](https://www.europeanpaymentscouncil.eu/sites/default/files/KB/files/EPC069-12%20v2.1%20Quick%20Response%20Code%20-%20Guidelines%20to%20Enable%20the%20Data%20Capture%20for%20the%20Initiation%20of%20a%20SCT.pdf)). The amount of the donation can possibly be modified in your Mobile Banking App.
| 5 EUR      | 10 EUR      |
|------------|-------------|
| <img src="https://user-images.githubusercontent.com/16196363/110995648-000cff80-837b-11eb-83a7-7a8c0e0f6996.png" width="80" height="80"> | <img src="https://user-images.githubusercontent.com/16196363/110995669-08fdd100-837b-11eb-98f9-aa32446b5b28.png" width="80" height="80"> |

## Use PayPal
[![](https://www.paypalobjects.com/en_US/BE/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=AT4L7ST55JR4A) 

# Domoticz-iROBOT-ROOMBA-plugin
Domoticz plugin for the support of the iRobot ROOMBA vacuum robot cleaner. It is tested with the ROOMBA i7. 

It enables you to manage the following functions:
* Start/stop cleaning (when stopping, the vacuum cleaner returns automatically to its docking station)
* Status of the vacuum cleaner (charging, running, docking, ...)

It could easily extended with other functions, however so far it gives me all I need for my home automation (eg ROOMBA is running while I am not at home).

The plugin is based on MQTT (https://en.wikipedia.org/wiki/MQTT).

## Installation (linux)
Follow this procedure to install the plugin.

### Install Domoticz plugin
Copy all the files in folder `/home/pi/domoticz/plugin/Roomba`.
If the domoticz folder is not located in `/home/pi`, adapt also the folder references further in these instructions.

### Install MQTT Broker (mosquitto)
* Install the python paho-mqtt library with `sudo pip3 install paho-mqtt`
* Install mosquitto with `sudo apt install mosquitto`
* It is adviced to change the mosquitto configuration file (by default in /etc/mosquitto/mosquitto.conf)
  * persistence false
  * log_dest none
* Start the service with `sudo service mosquitto start`

### Get the ROOMBA information
* Get the local IP address of your ROOMBA (often starting with 192.168.x.yyy and x=0 or 1). You can retrieve it from your router. Alternatively you can use tools like nmap (eg `nmap -sP 192.168.0.*`). The local IP address if furthere reference to as `ROOMBA_IP`.
* Get the BLID/Password of the ROOMBA
  * Install the six python library with `sudo pip3 install six`
  * Go to the folder /home/pi/domoticz/plugins/Roomba with `cd /home/pi/domoticz/plugins/Roomba/`
  * run `python3 ./roomba/getpassword.py -R ROOMBA_IP` and follow the instructions. Shortly the vacuum cleaner must be docked and you need to HOLD the HOME button for some seconds until a sound is played (the WIFI indicator on the ROOMBA will flash).
  * If all went well, there should be a `config.ini` file in the folder `/home/pi/domoticz/plugins/Roomba/`. You can check the content with `cat config.ini` and will find the `ROOMBA_IP`, blid, password and some other data about the ROOMBA vaccum cleaner.

### Create ROOMBA Client to get information and forward to MQTT Broker
`roomba` is a python3 module that acts as MQTT Client and forward the informaton to a MQTT Broker. It is based on Nick Waterton's work (https://github.com/NickWaterton/Roomba980-Python).
It can be started manually by `python3 roomba --topic /roomba/feedback/# --broker localhost --brokerFeedback /roomba/feedback --mapPath '' --mapSize '' --log ''` from the folder `/home/pi/domoticz/plugin/Roomba`. The arguments have the following meaning:
  * --topic: information/topics subscribed from the ROOMBA
  * --broker: (IP)Address of the MQTT Broker/Server
  * --brokerFeedback: information/topics from the ROOMBA sent to the MQTT Broker
  * --mapPath: set to '' to avoid creating html files and disable map creation
  * --mapsSize: set to '' to avoid creating html files and disable map creation
  * --log: set to '' to avoid creating log file on disk
It is possible to add more debug information by adding the argument `--debug` to the 

Create a service to start up the client automatically on boot of your domoticz server (stop the python script manually if it would have been started manually before):
* Create a file `/etc/systemd/system/roomba.service` with the following content (be sure that the folder `/home/pi/domoticz/plugins/Roomba/roomba` is already copied).
```
[Unit]
Description=Roomba mqtt client
After=network.target mosquitto.service

[Service]
Type=simple
Restart=always
RestartSec=10
User=pi
ExecStart=/usr/bin/python3 /home/pi/domoticz/plugins/Roomba/roomba --configfile /home/pi/domoticz/plugins/Roomba/config.ini --topic /roomba/feedback/# --broker localhost --brokerFeedback /roomba/feedback --mapPath '' --mapSize '' --log ''

[Install]
WantedBy=multi-user.target
```
* To start up the service at boot, execute `sudo systemctl enable roomba`
* Start the service with `sudo service roomba start`
* You can check if the service is correctly started with `sudo service roomba status` (should show `active (running)`)

### Add the device in Domoticz
Use the `Setup - Hardware` menu to add your ROOMBA to Domoticz. Select the device type `Roomba` and you are done.
If all goes well two devices are created, one in the `Switches` (to start/stop) and one in the `Utilities` (status of the ROOMBA).
Remark: there is no ROOMBA icon on the device showing the status. This is a restriction of Domoticz that does not allow to change the icon for a text device.

## Updating from mqtt_Roomba.py to roomba module (linux)
When having installed the previous version of the plugin (service based on mqtt_Roomba.py), please follow the instuctions here:
 * Download the new files
 * Stop the service with `sudo service roomba stop`
 * Change the file `/etc/systemd/system/roomba.service` with the content specified in the chapter Create ROOMBA Client to get information and forward to MQTT Broker (only the Execstart changed)
 * Update the changes with the instruction `sudo systemctl daemon-reload`
 * Start the service with `sudo service roomba start`
 * Check the service is correcly running with `sudo service roomba status`

Success!

**Don't forget a small gift by using the donation button...**
