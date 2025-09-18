# modulos/loader.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QDialog
from PyQt5.QtCore import Qt, QTimer, QEventLoop
from PyQt5.QtGui import QColor, QPainter, QConicalGradient

class LoaderWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.angle = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_angle)
        self.timer.start(16)

    def update_angle(self):
        self.angle = (self.angle + 6) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(self.angle)
        gradient = QConicalGradient(0, 0, 0)
        gradient.setColorAt(0.0, QColor('#3498db'))
        gradient.setColorAt(0.5, QColor('#ccc'))
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(-25, -25, 50, 50)

