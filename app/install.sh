adb push monkey /data/local/tmp/
adb shell chmod u+x /data/local/tmp/monkey
adb push monkey.jar /data/local/tmp/
adb install -r -g MonitorService.apk
