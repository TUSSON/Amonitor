from subprocess import Popen, call, TimeoutExpired, PIPE
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
        ecall('adb install -r -g app/MonitorService.apk')
        super().install()

    def _start(self):
        cmds = 'adb shell am start com.rock_chips.monitorservice/.MainActivity'
        self.popen = Popen(cmds.split(), stdout=PIPE)
        Timer(0.1, self._processStartResult).start()

    def start(self):
        # try connect first for fast boot
        self.connect()
        self._start()

    def _processStartResult(self):
        fd = self.popen.stdout
        line1 = fd.readline().decode()
        line2 = fd.readline().decode()
        if line2.startswith('Error'):
            self.install()
            self._start()
        elif line1.startswith('Starting'):
            self.callCb('started')

    def connect(self):
        if self.url is None:
            print('need url for connect')
            return

        ecall('adb forward tcp:50000 tcp:50000')
        lib_opts = {'analyzeduration': '32', 'flags': 'low_delay'}
        self.player = MediaPlayer(self.url,
                                  callback=self._mediaPlayerCallback,
                                  lib_opts=lib_opts)
        self.connectedTimer = Timer(0.1, self._processConnectResult)
        self.connectedTimer.start()
        self.timer = 1

    def _mediaPlayerCallback(self, selector, value):
        self.connectedTimer.cancel()
        if selector == 'read:error':
            self.player.close_player()
            self.tryTimer = Timer(1, self.connect)
            self.tryTimer.start()

    def _processConnectResult(self):
        super().connect()

    def disconnect(self):
        if self.tryTimer:
            self.tryTimer.cancel()
        if self.player:
            self.player.close_player()
        super().disconnect()


class AMonkeyService(AService):
    def __init__(self, cb=None, url=None):
        super().__init__(cb)
        self.url = url
        self.monkey = None
        self.tryTimer = None

    def install(self):
        ecall('adb push app/monkey.jar /data/local/tmp/')
        ecall('adb push app/monkey /data/local/tmp/')
        ecall('adb shell chmod u+x /data/local/tmp/monkey')
        super().install()

    def start(self):
        cmds = 'adb shell /data/local/tmp/monkey --port 50001'
        self.popen = Popen(cmds.split(), stdout=PIPE)
        Timer(0.1, self._processStartResult).start()

    def _processStartResult(self):
        try:
            self.popen.wait(1)
            fd = self.popen.stdout
            line = fd.readline().decode()
            if not line.startswith('Error binding'):
                self.install()
                self.start()
                return
        except TimeoutExpired:
            pass
        super().start()

    def connect(self):
        if self.url is None:
            print('need url for connect')
            return

        ecall('adb forward tcp:50001 tcp:50001')
        try:
            monkey = Monkey(self.url)
        except OSError:
            self.tryTimer = Timer(1, self.connect)
            self.tryTimer.start()
            return
        self.monkey = monkey
        self.tryTimer = Timer(0.2, self._processConnectResult)
        self.tryTimer.start()

    def _processConnectResult(self):
        ret = self.monkey.getvar('build.id')
        print('ret:', ret)
        if ret != 'FAILED' and len(ret) > 0:
            super().connect()
        else:
            self.connect()

    def disconnect(self):
        if self.tryTimer:
            self.tryTimer.cancel()
        if self.monkey:
            self.monkey.quit()
            self.monkey = None
        super().disconnect()
