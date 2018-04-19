#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QApplication, QMenu,
                             QFrame, QSizePolicy)
from PyQt5.QtGui import QPixmap, QImage, QIcon
from PyQt5.QtCore import QThread, QBasicTimer, Qt, QEvent, QSize, QRect
from ffpyplayer.pic import Image
from ffpyplayer.player import MediaPlayer
from subprocess import Popen, call
import sys, time, os
from threading import Timer
from monkey import Monkey
from aservice import AMonitorService, AMonkeyService, getCurrentPath, getDeviceId
from keymap import vkeyToAndroidMaps
import pickle

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
        self.timer = QBasicTimer()
        self.device = None
        self.config = {}
        self.configFile = getCurrentPath() + '/.devconfig'
        self.devconfig = None
        self.loadConfig()
        self.initService(url, monkeyUrl)
        self.initUI()
        self.timercount = 0
        self.framecount = 0
        self.timer.start(15, self)

    def setDefaultConfig(self):
        if self.devconfig is None:
            self.devconfig = {}
        if 'navbar' not in self.devconfig:
            self.devconfig['navbar'] = True
        if 'geometry' not in self.devconfig:
            self.devconfig['geometry'] = QRect(600, 100, 300, 350)
        if 'res' not in self.devconfig:
            self.devconfig['res'] = [1080, 1920]
        if 'isNewMonkey' not in self.devconfig:
            self.devconfig['isNewMonkey'] = True

    def loadConfig(self):
        if self.device is None:
            device = getDeviceId()
            if device:
                self.device = device
        if self.device:
            try:
                with open(self.configFile, 'rb') as f:
                    self.config = pickle.load(f)
                    if self.device in self.config:
                        self.devconfig = self.config[self.device]
            except (FileNotFoundError, KeyError, TypeError):
                pass
            self.setDefaultConfig()

    def saveConfig(self):
        if not self.device:
            return
        self.devconfig['navbar'] = self.hboxframe.isVisible()
        self.devconfig['geometry'] = self.geometry()
        self.devconfig['res'] = [int(self.dw), int(self.dh)]
        self.devconfig['isNewMonkey'] = self.monkeyService.isNewMonkey
        self.config[self.device] = self.devconfig
        with open(self.configFile, 'wb') as f:
            pickle.dump(self.config, f, pickle.HIGHEST_PROTOCOL)
            print('save config:', self.config)

    def initService(self, url, monkeyUrl):
        print('{} initService: {}'.format(time.monotonic(), 'start'))
        # start screen monitor service
        self.player = None
        self.monitorService = AMonitorService(
                cb=self.monitorStatusChanged, url=url)
        self.monitorService.start()
        # start monkey service
        self.monkey = None
        tryNewCnt = 1 if self.devconfig['isNewMonkey'] else 0
        self.monkeyService = AMonkeyService(
            cb=self.monkeyStatusChanged,
            url=monkeyUrl, tryNewCnt=tryNewCnt)
        self.monkeyService.start()

    def initUI(self):
        self.dw, self.dh = self.devconfig['res']
        self.setGeometry(self.devconfig['geometry'])
        self.ratio = self.dh / self.dw
        self.scrolltimer = None
        self.scrollstep = 0
        self.resizetimer = None

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        self.lbl = QLabel(self)
        self.lbl.setScaledContents(True)
        self.lbl.setMinimumSize(200, 200)
        self.lbl.setFocusPolicy(Qt.NoFocus)
        vbox.addWidget(self.lbl)

        hbox = QHBoxLayout()
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
        self.hboxframe.setVisible(self.devconfig['navbar'])
        self.updateTitleStatus('≠')
        self.show()

    def monitorStatusChanged(self, status):
        print('{} monitor: {}'.format(time.monotonic(), status))
        if status == 'connected':
            self.player = self.monitorService.player
        elif status == 'disconnected':
            self.player = None
            self.updateTitleStatus('≠')

    def monkeyStatusChanged(self, status):
        print('{} monkey: {}'.format(time.monotonic(), status))
        if status == 'connected':
            self.monkey = self.monkeyService.monkey
            self.updateDeviceRes()
            if self.framecount > 0:
                self.updateTitleStatus()
        elif status == 'disconnected':
            self.monkey = None
            self.updateTitleStatus('≠')

    def updateTitleStatus(self, status='', fps=0):
        txt = 'amonitor ' + status
        if fps > 0:
            txt = 'amonitor fps: {}'.format(fps)
        self.setWindowTitle(txt)

    def updateDeviceRes(self):
        try:
            dw = int(self.monkey.getvar('display.width'))
            dh = int(self.monkey.getvar('display.height'))
        except ValueError:
            print('get device resolution failed!')
            return

        hdiff = [dw * r - dh for r in (4/3, 16/9, 18/9)]
        diff = 0
        for d in hdiff:
            if d >= 0:
                diff = d
                break

        self.dw = dw
        self.dh = dh + diff
        print('device res is', self.dw, 'x', self.dh, 'diff:', diff)

    def update(self):
        if self.player is None:
            return

        self.timercount += 1
        frame, val = self.player.get_frame()
        iw = ih = 0
        if val == 'eof':
            pass
        elif frame is not None:
            if self.framecount == 0:
                print('{} first frame'.format(time.monotonic()))
            img, t = frame
            iw, ih = img.get_size()
            ratio = ih / iw
            if ratio != self.ratio:
                self.ratio = ratio
                self.requstResize()
            imgbyte = img.to_bytearray()[0]
            qimg = QImage(imgbyte, iw, ih, QImage.Format_RGB888)
            '''
            w = self.lbl.width()
            h = self.lbl.height()
            simg = qimg.scaled(w, h, Qt.KeepAspectRatio,
                               Qt.SmoothTransformation)
            '''
            self.lbl.setPixmap(QPixmap(qimg))
            if self.timercount > 200:
                fps = int(self.framecount / 3)
                if fps > 0:
                    self.updateTitleStatus(fps=fps)
                print('iw:', iw, 'ih:', ih, 'fps: ', fps)
                self.framecount = 0
                self.timercount = 0
            self.framecount += 1

    def timerEvent(self, event):
        self.update()

    def resizeKeepRatio(self):
        fw = self.width()
        fh = self.height()
        iw = self.lbl.width()
        ih = self.lbl.height()
        oh = fh - ih
        print('resize:', iw, ih)
        if self.ratio > 1:
            iw = min(iw, ih)
            ih = int(iw * self.ratio + 0.5)
        else:
            ih = min(iw, ih)
            iw = int(ih / self.ratio + 0.5)
        ih += oh

        if fw != iw or fh != ih:
            self.resize(iw, ih)

    def requstResize(self):
        dh = max(self.dw, self.dh)
        dw = min(self.dw, self.dh)
        if self.ratio > 1:
            self.dh = dh
            self.dw = dw
        else:
            self.dw = dh
            self.dh = dw
        if self.resizetimer:
            self.resizetimer.cancel()
        self.resizetimer = Timer(0.2, self.resizeKeepRatio)
        self.resizetimer.start()

    def resizeEvent(self, event):
        self.requstResize()

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
        if self.monkey:
            if key in vkeyToAndroidMaps:
                dkey = vkeyToAndroidMaps[key]
                #print('key press:', dkey)
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

    def injectAllowMonitor(self):
        if self.monkey:
            self.monkey.press('KEYCODE_TAB')
            time.sleep(0.1)
            self.monkey.press('KEYCODE_DPAD_CENTER')
            time.sleep(0.1)
            self.monkey.press('KEYCODE_DPAD_DOWN')
            time.sleep(0.1)
            self.monkey.press('KEYCODE_DPAD_RIGHT')
            time.sleep(0.1)
            self.monkey.press('KEYCODE_DPAD_CENTER')

    def rotate(self, degree):
        if self.monkey:
            self.monkey.rotate(degree)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        navbar = menu.addAction("Show/Hide Navigation Bar")
        rotate = []
        if self.monkey and self.monkeyService.isNewMonkey:
            rotateMenu = QMenu('Rotate', menu)
            menu.addMenu(rotateMenu)
            rotate = [rotateMenu.addAction(i) for i in ['Portrait', 'Landscape']]
        injectAllow = -1
        if self.monkey and self.framecount == 0:
            injectAllow = menu.addAction("InjectAllowMonitor")
        action = menu.exec_(self.mapToGlobal(event.pos()))
        if navbar == action:
            self.hboxframe.setVisible(not self.hboxframe.isVisible())
            self.resize(self.width(), self.height() + 1)
        elif injectAllow == action:
            self.injectAllowMonitor()
        elif action in rotate:
            index = rotate.index(action)
            self.rotate(index)

    def closeEvent(self, event):
        self.saveConfig()
        self.timer.stop()
        self.monitorService.stop()
        self.monkeyService.stop()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Monitor('tcp://127.0.0.1:50000', 'tcp://127.0.0.1:50001')
    print('exit Done!', sys.exit(app.exec_()))
