from subprocess import Popen, call, TimeoutExpired, PIPE, STDOUT
from threading import Timer
from ffpyplayer.player import MediaPlayer
from monkey import Monkey
import time


def ecall(cmds):
    return call(cmds.split(' '))

class AService:
    def __init__(self, cb=None):
        self.cb = cb
        pass

    def callCb(self, status=None):
        if self.cb:
            self.cb(status)

    def install(self):
        self.callCb('installed')

    def start(self):
        self.callCb('started')
        self.connect()

    def stop(self):
        self.disconnect()
        self.callCb('stoped')

    def connect(self):
        self.callCb('connected')

    def disconnect(self):
        self.callCb('disconnected')


class AMonitorService(AService):
    def __init__(self, cb=None, url=None):
        super().__init__(cb)
        self.url = url
        self.player = None
        self.tryTimer = None

    def install(self):
        ret = ecall('adb install -r -g app/MonitorService.apk')
        if ret == 0:
            super().install()

    def _start(self):
        cmds = 'adb shell am start com.rock_chips.monitorservice/.MainActivity'
        self.popen = Popen(cmds.split(), stdout=PIPE, stderr=STDOUT)
        Timer(0.1, self._processStartResult).start()

    def start(self):
        self.needStop = False
        # try connect first for fast boot
        self.connect()
        self._start()

    def _processStartResult(self):
        fd = self.popen.stdout
        line1 = fd.readline().decode()
        line2 = fd.readline().decode()
        if line1.startswith('Starting') and not line2.startswith('Error'):
            self.callCb('started')
            return
        time.sleep(1)
        if self.needStop:
            return
        # try install and start again
        self.popen = None
        self.install()
        self._start()

    def stop(self):
        self.popen = None
        self.needStop = True
        self.disconnect()
        self.callCb('stoped')

    def connect(self):
        if self.needStop:
            return
        if self.url is None:
            print('need url for connect')
            return

        ecall('adb forward tcp:50000 tcp:50000')
        lib_opts = {'analyzeduration': '32', 'flags': 'low_delay'}
        if self.player:
            self.player.close_player()
            self.player = None
        self.player = MediaPlayer(self.url,
                                  callback=self._mediaPlayerCallback,
                                  lib_opts=lib_opts)
        self.connectedTimer = Timer(0.1, self._processConnectResult)
        self.connectedTimer.start()

    def _mediaPlayerCallback(self, selector, value):
        if self.connectedTimer:
            self.connectedTimer.cancel()
            self.connectedTimer = None

        if selector in ('read:error', 'eof'):
            self.callCb('disconnected')
            self.tryTimer = None
            self.tryTimer = Timer(1, self.connect)
            self.tryTimer.start()

    def _processConnectResult(self):
        super().connect()

    def disconnect(self):
        if self.tryTimer:
            self.tryTimer.cancel()
            self.tryTimer = None
        if self.player:
            self.player.close_player()
        super().disconnect()


class AMonkeyService(AService):
    def __init__(self, cb=None, url=None):
        super().__init__(cb)
        self.url = url
        self.monkey = None
        self.tryTimer = None
        self.watchDogTimer = None

    def install(self):
        ret = ecall('adb push app/monkey.jar /data/local/tmp/')
        ret |= ecall('adb push app/monkey /data/local/tmp/')
        ret |= ecall('adb shell chmod u+x /data/local/tmp/monkey')
        if ret == 0:
            super().install()

    def _start(self):
        cmds = 'adb shell /data/local/tmp/monkey --port 50001'
        self.popen = Popen(cmds.split(), stdout=PIPE, stderr=STDOUT)
        self.tryTimer = Timer(0.1, self._processStartResult)
        self.tryTimer.start()

    def start(self):
        self.needStop = False
        self._start()

    def _processStartResult(self):
        try:
            self.popen.wait(1)
            fd = self.popen.stdout
            line = fd.readline().decode()
            time.sleep(1)
            if self.needStop:
                return
            if not line.startswith('Error binding'):
                # try install and start again
                self.popen = None
                self.install()
                self._start()
                return
        except TimeoutExpired:
            pass
        super().start()

    def stop(self):
        self.needStop = True
        self.disconnect()
        self.popen = None
        self.callCb('stoped')

    def connect(self):
        if self.needStop:
            return
        if self.url is None:
            print('need url for connect')
            return

        ecall('adb forward tcp:50001 tcp:50001')
        try:
            monkey = Monkey(self.url)
        except OSError:
            self.tryTimer = None
            self.tryTimer = Timer(1, self.connect)
            self.tryTimer.start()
            return
        self.monkey = monkey
        self.tryTimer = Timer(0.2, self._processConnectResult)
        self.tryTimer.start()

    def _processConnectResult(self):
        ret = self.monkey.getvar('build.id')
        if ret != 'FAILED' and len(ret) > 0:
            # connected
            super().connect()
            # start watchDogTimer
            if self.watchDogTimer:
                self.watchDogTimer.cancel()
                self.watchDogTimer = None
            self.watchDogTimer = Timer(2, self.watchDogDetect)
            self.watchDogTimer.start()
        else:
            # retry connect
            self.monkey = None
            self.connect()

    def watchDogDetect(self):
        self.watchDogTimer = None
        ret = self.monkey.getvar('build.id')
        if ret != 'FAILED' and len(ret) > 0:
            self.watchDogTimer = Timer(2, self.watchDogDetect)
            self.watchDogTimer.start()
        else:
            # restart service
            self._start()

    def disconnect(self):
        if self.watchDogTimer:
            self.watchDogTimer.cancel()
            self.watchDogTimer = None

        if self.tryTimer:
            self.tryTimer.cancel()
            self.tryTimer = None
        if self.monkey:
            self.monkey.quit()
            self.monkey = None
        super().disconnect()
