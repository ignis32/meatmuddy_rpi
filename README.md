# meatmuddy_rpi
Raspberry pi midi drum machine


# Enable USB gadget mode with midi: RPI0, 

Raspbian Bullseye

 /boot/config.txt

```
[all]
dtoverlay=dwc2
```
/etc/modules/


```
dwc2,g_midi
```

# add current user to audio group to allow access to midi ports:

sudo usermod -aG audio <username>

# add g_midi to /etc/rc.local before exit 0

modprobe g_midi



Check that port appeared:
```
$ amidi -l
Dir Device    Name
IO  hw:1,0    f_midi
```
# install deps

sudo apt install python3-pip
sudo apt-get install librtmidi-dev 

pip install -r requirements.txt
pip install python-rtmidi  # takes time.




# clean unused services

sudo systemctl disable bluetooth
sudo systemctl stop bluetooth

sudo systemctl disable hciuart
sudo systemctl stop hciuart

sudo systemctl disable hciuart.service
sudo systemctl stop hciuart.service
sudo systemctl disable bluealsa.service
sudo systemctl stop bluealsa.service
sudo systemctl disable bluetooth.service
sudo systemctl stop bluetooth.service

sudo systemctl disable triggerhappy
sudo  systemctl stop triggerhappy 

sudo systemctl disable  systemd-timesyncd
sudo systemctl stop    systemd-timesyncd

systemctl disable ModemManager.service
systemctl stop ModemManager.service
# Disable Bluetooth
dtoverlay=disable-bt