# Donation
It took me quite some effort to get the plugin available. Small contributions are welcome...

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

### Install MQTT ROOMBA Client
`mqtt_Roomba.py` is a python3 script that acts as MQTT Client. It is based on Nick Waterton's work (https://github.com/NickWaterton/Roomba980-Python).
It can be started manually by `python3 mqtt_Roomba.py`. Use the optional parameter -D if debug output is required (eg `python3 mqtt_Roomba.py -D 3`).

Create a service to start up the client automatically on boot of your domoticz server (stop the python script manually if it would have been started manually before):
* Create a file `/etc/systemd/system/roomba.service` with the following content (be sure that the file `/home/pi/domoticz/plugins/Roomba/mqtt_Roomba.py` is already copied)
```
[Unit]
Description=Roomba mqtt client
After=network.target mosquitto.service

[Service]
Type=simple
Restart=always
RestartSec=10
User=pi
ExecStart=/usr/bin/python3 /home/pi/domoticz/plugins/Roomba/mqtt_Roomba.py

[Install]
WantedBy=multi-user.target
```
* Start the service with `sudo service roomba start`

### Get the ROOMBA information
* Get the local IP address of your ROOMBA (often starting with 192.168.x.yyy and x=0 or 1). You can retrieve it from your router. Alternatively you can use tools like nmap (eg `nmap -sP 192.168.0.*`). The local IP address if furthere reference to as `ROOMBA_IP`.
* Get the BLID/Password of the ROOMBA
  * Install the six python library with `sudo pip3 install six`
  * Go to the folder /home/pi/domoticz/plugins/Roomba with `cd /home/pi/domoticz/plugins/Roomba/`
  * run `python3 ./roomba/getpassword.py -R ROOMBA_IP` and follow the instructions. Shortly the vacuum cleaner must be docked and you need to HOLD the HOME button for some seconds until a sound is played (the WIFI indicator on the ROOMBA will flash).
  * If all went well, there should be a `config.ini` file in the folder `/home/pi/domoticz/plugins/Roomba/`. You can check the content with `cat config.ini` and will find the `ROOMBA_IP`, blid, password and some other data about the ROOMBA vaccum cleaner.

### Add the device in Domoticz
Use the `Setup - Hardware` menu to add your ROOMBA to Domoticz. Select the device type `Roomba` and you are done.
If all goes well two devices are created, one in the `Switches` (to start/stop) and one in the `Utilities` (status of the ROOMBA).
Remark: there is no ROOMBA icon on the device showing the status. This is a restriction of Domoticz that does not allow to change the icon for a text device.

Success!

**Don't forget a small gift by using the donation button...**
