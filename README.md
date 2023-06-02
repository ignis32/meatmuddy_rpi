# meatmuddy_rpi
Raspberry pi midi drum machine


# Enable USB gadget mode with midi: RPI4




 /boot/config.txt

```
[all]
dtoverlay=dwc2
```
/etc/modules/


```
g_midi
```


Check that port appeared:
```
$ amidi -l
Dir Device    Name
IO  hw:1,0    f_midi
```
