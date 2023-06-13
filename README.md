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


