#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QApplication, QMenu,
                             QFrame, QSizePolicy)
from PyQt5.QtGui import QPixmap, QImage, QIcon
from PyQt5.QtCore import QThread, QBasicTimer, Qt, QEvent, QSize
from ffpyplayer.pic import Image
from ffpyplayer.player import MediaPlayer
from subprocess import Popen, call
import sys, time
from threading import Timer
from monkey import Monkey
from keymap import vkeyToAndroidMaps

'''
TODO:
    * support bit-rate, encode resolution config
    * support rotate
    * support record operation event and replay
'''

class KeyButton(QPushButton):
    def __init__(self, text='', icon=None, parent=None, keycode=None):
        if icon:
            super().__init__(QIcon(icon), text)
        else:
            super().__init__(text)
        self.parent = parent
        self.keycode = keycode
        self.setMinimumWidth(16)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFlat(True)
        self.setFocusPolicy(Qt.NoFocus)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self.parent and self.keycode and self.parent.monkey:
            self.parent.monkey.press(self.keycode)


class Monitor(QWidget):
    def __init__(self, url, monkeyUrl=None,  parent=None):
        super().__init__(parent)
        self.url = url
        self.monkeyUrl = monkeyUrl
        self.timer = QBasicTimer()
        self.initUI()
        self.connect()
        self.framecount = 0
        self.timercount = 0
        self.timer.start(15, self)

    def initUI(self):
        self.setGeometry(600, 100, 300, 400)
        self.ratio = self.height() / self.width()
        self.scrolltimer = None
        self.scrollstep = 0

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        self.lbl = QLabel(self)
        self.lbl.setScaledContents(True)
        self.lbl.setMinimumSize(200, 200)
        self.lbl.setFocusPolicy(Qt.NoFocus)
        vbox.addWidget(self.lbl)

        hbox = QHBoxLayout(self)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)
        bn_vu = KeyButton('🔊', None, self, 'KEYCODE_VOLUME_UP')
        bn_vd = KeyButton('🔉', None, self, 'KEYCODE_VOLUME_DOWN')
        bn_bk = KeyButton('◀', None, self, 'KEYCODE_BACK')
        bn_hm = KeyButton('●', None, self, 'KEYCODE_HOME')
        bn_mn = KeyButton('■', None, self, 'KEYCODE_APP_SWITCH')
        bn_pw = KeyButton('🔌', None, self, 'KEYCODE_POWER')
        hbox.addWidget(bn_pw, 2)
        hbox.addWidget(bn_bk, 3)
        hbox.addWidget(bn_hm, 4)
        hbox.addWidget(bn_mn, 3)
        hbox.addWidget(bn_vd, 1)
        hbox.addWidget(bn_vu, 1)
        hboxframe = QWidget()
        hboxframe.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        hboxframe.setContentsMargins(0, 0, 0, 0)
        hboxframe.setLayout(hbox)
        vbox.addWidget(hboxframe)
        self.vbox = vbox
        self.hboxframe = hboxframe

        self.setWindowTitle('amonitor')
        self.show()

    def connect(self):
        call('adb forward tcp:50000 tcp:50000'.split(' '))
        call('adb forward tcp:50001 tcp:50001'.split(' '))
        monkeycmds = 'adb shell /data/local/tmp/monkey --port 50001'
        servicecmds = 'adb shell am start com.rock_chips.monitorservice/.MainActivity'
        stopservicecmds = 'adb shell am force-stop com.rock_chips.monitorservice'
        call(stopservicecmds.split(' '))
        call(servicecmds.split(' '))
        self.dw = 1080
        self.dh = 1920
        self.pmonkey = None
        if self.monkeyUrl:
            self.pmonkey = Popen(monkeycmds.split(' '))
        self.player = None
        self.monkey = None
        self.monkeyTimer = None
        if self.monkeyUrl:
            self.monkeyTimer = Timer(2, self.connectMonkey)
            self.monkeyTimer.start()
        self.monitorTimer = None
        self.connectMonitor()

    def disConnect(self):
        if self.monkeyTimer:
            self.monkeyTimer.cancel()
        if self.monitorTimer:
            self.monitorTimer.cancel()
        self.player.close_player()
        self.player = None
        if self.monkey:
            self.monkey.quit()
            self.monkey = None
        if self.pmonkey:
            self.pmonkey.kill()
            self.pmonkey.wait()
            self.pmonkey = None

    def connectMonitor(self):
        lib_opts = {'analyzeduration': '32', 'flags': 'low_delay'}
        player = self.player
        self.player = None
        if player:
            player.close_player()
        self.player = MediaPlayer(self.url,
                                  callback=self.mediaPlayerCallback,
                                  lib_opts=lib_opts)

    def mediaPlayerCallback(self, selector, value):
        print('callback:', selector)
        if selector == 'read:error':
            self.monitorTimer = Timer(1, self.connectMonitor)
            self.monitorTimer.start()

    def connectMonkey(self):
        self.monkeyTimer = None
        try:
            self.monkey = Monkey(self.monkeyUrl)
        except OSError:
            return

        try:
            dw = int(self.monkey.getvar('display.width'))
            dh = int(self.monkey.getvar('display.height'))
        except ValueError:
            return

        self.dw = dw
        self.dh = dh
        print('device res is', self.dw, 'x', self.dh)

    def update(self):
        if self.player is None:
            return

        self.timercount += 1
        frame, val = self.player.get_frame()
        iw = ih = 0
        if val == 'eof':
            pass
        elif frame is not None:
            img, t = frame
            iw, ih = img.get_size()
            ratio = ih / iw
            if ratio != self.ratio:
                self.ratio = ratio
                self.resize(self.width()+1, self.height())
            imgbyte = img.to_bytearray()[0]
            qimg = QImage(imgbyte, iw, ih, QImage.Format_RGB888)
            '''
            w = self.lbl.width()
            h = self.lbl.height()
            simg = qimg.scaled(w, h, Qt.KeepAspectRatio,
                               Qt.SmoothTransformation)
            '''
            self.lbl.setPixmap(QPixmap(qimg))
            self.framecount += 1
            if self.timercount > 200:
                print('iw:', iw, 'ih:', ih, 'fps: ', int(self.framecount / 3))
                self.framecount = 0
                self.timercount = 0

    def timerEvent(self, event):
        self.update()

    def resizeEvent(self, event):
        nh = int(self.lbl.width() * self.ratio + 0.5)
        oh = self.height() - self.lbl.height()
        ih = nh + oh
        if self.height() != ih:
            self.resize(self.lbl.width(), ih)

    def getDeviceXY(self, pos):
        dx = pos.x() * self.dw / self.lbl.width()
        dx = min(max(0, dx), self.dw)
        dy = pos.y() * self.dh / self.lbl.height()
        dy = min(max(0, dy), self.dh)
        return int(dx), int(dy)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.monkey:
            dx, dy = self.getDeviceXY(event.pos())
            self.monkey.touchDown(dx, dy)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.monkey:
            dx, dy = self.getDeviceXY(event.pos())
            self.monkey.touchUp(dx, dy)

    def mouseMoveEvent(self, event):
        if self.monkey:
            dx, dy = self.getDeviceXY(event.pos())
            self.monkey.touchMove(dx, dy)

    def deviceScroll(self, step):
        self.monkey.scroll(0, step)
        self.scrolltimer = None

    def wheelEvent(self, event):
        if self.monkey:
            step = event.angleDelta().y()
            self.scrollstep -= step
            step = int(self.scrollstep / 120)
            if self.scrolltimer is None and step != 0:
                self.scrollstep = int(self.scrollstep - step * 120)
                self.scrolltimer = Timer(0.1, self.deviceScroll, [step])
                self.scrolltimer.start()

    def keyPressEvent(self, event):
        key = event.key()
        print('key press:', key)
        if self.monkey:
            if key in vkeyToAndroidMaps:
                dkey = vkeyToAndroidMaps[key]
                self.monkey.keyDown(dkey)
            else:
                text = event.text()
                if text.isprintable():
                    self.monkey.type(text)

    def keyReleaseEvent(self, event):
        key = event.key()
        if self.monkey:
            if key in vkeyToAndroidMaps:
                dkey = vkeyToAndroidMaps[key]
                self.monkey.keyUp(dkey)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        reconnect = menu.addAction("ReConnect")
        navbar = menu.addAction("Show/Hide Navigation Bar")
        injectAllow = -1
        if self.monkey and self.framecount == 0:
            injectAllow = menu.addAction("InjectAllowMonitor")
        action = menu.exec_(self.mapToGlobal(event.pos()))
        if navbar == action:
            self.hboxframe.setVisible(not self.hboxframe.isVisible())
            self.resize(self.width(), self.height() + 1)
        elif reconnect == action:
            self.disConnect()
            self.connect()
        elif injectAllow == action:
            print('injectAllow')
            self.monkey.press('KEYCODE_TAB')
            time.sleep(0.1)
            self.monkey.press('KEYCODE_DPAD_CENTER')
            time.sleep(0.1)
            self.monkey.press('KEYCODE_DPAD_DOWN')
            time.sleep(0.1)
            self.monkey.press('KEYCODE_DPAD_RIGHT')
            time.sleep(0.1)
            self.monkey.press('KEYCODE_DPAD_CENTER')

    def closeEvent(self, event):
        self.timer.stop()
        self.disConnect()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Monitor('tcp://127.0.0.1:50000', 'tcp://127.0.0.1:50001')
    print('exit Done!', sys.exit(app.exec_()))
