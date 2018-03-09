# Amonitor
- [x] Device tested on Android 6.0, 7.1
- [x] PC tested on mac 10.13.3 and ubuntu 16.04
- [x] no root need
- [x] screen monitoring
- [x] keyboard/touch spport
- [x] navigation bar
- [x] rotate screen
- [x] auto install app and  auto reconnect
- [ ] Input events record and replay
- [ ] screenshot, screen record
- [ ] bit-rate, encode resolution config

## What it is ?
High frame rate low latency and free open source screen monitor for Android (like vysor).
[Video Demo](https://youtu.be/7b2aqHIDLZQ)
[![Demo Amonitor](https://github.com/TUSSON/Amonitor/blob/master/res/demo.gif)](https://youtu.be/7b2aqHIDLZQ)

## Requirements
- [python3](https://www.python.org/downloads/)
- [pyqt5](http://pyqt.sourceforge.net/Docs/PyQt5/installation.html)
- [ffpyplayer](http://https://matham.github.io/ffpyplayer/installation.html)
- [adb](https://developer.android.com/studio/command-line/adb.html)

## Installation
- Make sure all the requirements are ready.
- [Connect phone and enable adb](https://developer.android.com/studio/command-line/adb.html#Enabling)
- Run amonitor
```
./amonitor.py
```

## Problems
1. Latency too large, last frame not update.
> Please enable floating window permission.

2. The device's screen or touchscreen is bad, how to enable the permissions?
> please try 'InjectAllowMonitor' action in the right-click menu.
