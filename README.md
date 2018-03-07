# Amonitor
- [x] Device tested on Android 6.0, 7.1
- [x] PC tested on mac 10.13.3 and ubuntu 16.04
- [x] no root need
- [x] screen monitoring
- [x] keyboard/touch spport
- [x] navigation bar
- [ ] rotate screen
- [ ] Input events record and replay
- [ ] screenshot, screen record
- [ ] bit-rate, encode resolution config

## What it is ?
High frame rate low latency and free open source screen monitor for Android (like vysor).
[Video Demo](https://youtu.be/7b2aqHIDLZQ)
[![Demo Amonitor](https://github.com/TUSSON/Amonitor/blob/master/res/demo.gif)](https://youtu.be/7b2aqHIDLZQ)

## Requirements
- [python3](https://www.python.org/downloads/)
- [ffpyplayer](http://https://matham.github.io/ffpyplayer/installation.html)
- [adb](https://developer.android.com/studio/command-line/adb.html)

## Installation
- Make sure all the requirements are ready.
- [Connect phone and enable adb](https://developer.android.com/studio/command-line/adb.html#Enabling)
- Install service app
```bash
cd app
./install.sh
cd ../
```
- Run amonitor
```
./amonitor.py
```

## Problems
1. Latency too large, last frame not update.
> Please enable floating window permission.