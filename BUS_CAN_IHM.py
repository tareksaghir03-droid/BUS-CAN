import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "BUS CAN", "CAN_BUS_old", "IHM")))
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QDialog, QLabel, QLCDNumber, QLineEdit, QHBoxLayout)
import can
import cubegl

nameport = '/dev/ttyACM0'
baudrate = 115200
CAN_BUS_NUMBER = 0
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def asset_path(filename):
    return os.path.join(BASE_DIR, filename)

# ---------------- ANEMO CODE ----------------
class ANEMODialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Anémomètre – Dashboard')
        self.setGeometry(400, 200, 520, 540)
        # Fond bleu très clair
        self.setStyleSheet("background: #e3f2fd;")
        from PyQt5.QtGui import QPixmap, QFont
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        # Carte centrale blanche
        card = QWidget()
        card.setStyleSheet("""
            background: #fff;
            border-radius: 28px;
            margin: 32px 32px 18px 32px;
            border: 2px solid #90caf9;
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(22)
        card_layout.setContentsMargins(36, 28, 36, 28)
        # Image stylisée
        anemo_img = QLabel()
        anemo_img.setAlignment(Qt.AlignCenter)
        anemo_img_path = asset_path("anemometre.png")
        anemo_img.setPixmap(QPixmap(anemo_img_path).scaled(90, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        anemo_img.setStyleSheet("margin-bottom: 8px;")
        card_layout.addWidget(anemo_img)
        # Titre moderne
        label = QLabel("ANÉMOMÈTRE")
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Segoe UI", 25, QFont.Bold))
        label.setStyleSheet("color: #185a9d; letter-spacing: 2px; margin-bottom: 0px;")
        card_layout.addWidget(label)
        # LCD et labels
        self.lcd_anemo = QLCDNumber(self)
        self.lcd_anemo.setStyleSheet("background: #fff; color: #1976d2; border: 2px solid #1976d2; border-radius: 10px; margin-bottom: 0px;")
        self.label_anemo = QLabel("Vitesse du vent (km/h)", self)
        self.label_anemo.setAlignment(Qt.AlignCenter)
        self.label_anemo.setStyleSheet("font-size: 18px; color: #1976d2; font-family: 'Segoe UI'; margin-bottom: 2px;")
        card_layout.addWidget(self.label_anemo)
        card_layout.addWidget(self.lcd_anemo)
        # Vitesse moteur
        self.label_edit_vitesse = QLabel("Vitesse du moteur")
        self.label_edit_vitesse.setStyleSheet("font-size: 15px; color: #185a9d; font-family: 'Segoe UI'; margin-top: 10px;")
        card_layout.addWidget(self.label_edit_vitesse)
        self.edit_vitesse = QLineEdit()
        self.edit_vitesse.setStyleSheet("padding: 8px; border-radius: 8px; border: 1.5px solid #90caf9; background: #fff; color: #185a9d; font-size: 15px;")
        card_layout.addWidget(self.edit_vitesse)
        # Boutons stylés bleu foncé
        btn_style = """
            QPushButton {
                background: #1976d2;
                color: #fff;
                font-size: 16px;
                font-family: 'Segoe UI';
                font-weight: bold;
                border-radius: 12px;
                border: none;
                padding: 10px 0px;
                margin: 8px 0px;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: #1565c0;
                color: #fff;
            }
        """
        send_can_moteur_vitesse = QPushButton("Envoyer vitesse moteur")
        send_can_moteur_vitesse.setStyleSheet(btn_style)
        send_can_moteur_vitesse.clicked.connect(self.sendMoteurVitesseCAN)
        card_layout.addWidget(send_can_moteur_vitesse)
        self.label_minimum_vitesse = QLabel("Vitesse minimale pour démarrer le moteur")
        self.label_minimum_vitesse.setStyleSheet("font-size: 15px; color: #185a9d; font-family: 'Segoe UI'; margin-top: 10px;")
        card_layout.addWidget(self.label_minimum_vitesse)
        self.minimum_vitesse = QLineEdit()
        self.minimum_vitesse.setStyleSheet("padding: 8px; border-radius: 8px; border: 1.5px solid #90caf9; background: #fff; color: #185a9d; font-size: 15px;")
        card_layout.addWidget(self.minimum_vitesse)
        send_can_anemo_vitesse = QPushButton("Définir vitesse minimale")
        send_can_anemo_vitesse.setStyleSheet(btn_style)
        send_can_anemo_vitesse.clicked.connect(self.sendAnemoVitesseCAN)
        card_layout.addWidget(send_can_anemo_vitesse)
        send_can_moteur = QPushButton("Démarrer / Arrêter le moteur")
        send_can_moteur.setStyleSheet(btn_style)
        send_can_moteur.clicked.connect(self.sendMoteurStatusCAN)
        card_layout.addWidget(send_can_moteur)
        send_can_moteur_start = QPushButton("Démarrer le moteur")
        send_can_moteur_start.setStyleSheet(btn_style)
        send_can_moteur_start.clicked.connect(self.startMotor)
        card_layout.addWidget(send_can_moteur_start)
        send_can_moteur_stop = QPushButton("Arrêter le moteur")
        send_can_moteur_stop.setStyleSheet(btn_style)
        send_can_moteur_stop.clicked.connect(self.stopMotor)
        card_layout.addWidget(send_can_moteur_stop)
        main_layout.addStretch(1)
        main_layout.addWidget(card, alignment=Qt.AlignCenter)
        main_layout.addStretch(1)
        # Elements Anemo (fonctions inchangées)
        self.bus = can.interface.Bus(channel=f"can{CAN_BUS_NUMBER}", bustype='socketcan')
        self.timer_anemo = QTimer()
        self.timer_anemo.timeout.connect(self.readCanDataAnemo)
        self.timer_anemo.start(1)
    def readCanDataAnemo(self):
        message = self.bus.recv(timeout=0.1)
        if message is not None:
            if message.arbitration_id == 24:
                value = int.from_bytes(message.data, byteorder='big')
                self.lcd_anemo.display(value)
    def sendSwitchStatusCAN(self):
        self.switch_state = (self.switch_state + 1) % 2
        frame_to_write = can.Message(
            arbitration_id=0x4,
            data=[self.switch_state],
            is_extended_id=False
        )
        self.bus.send(frame_to_write)
    def sendMoteurStatusCAN(self):
        self.moteur_state = (self.moteur_state + 1) % 2
        frame_to_write = can.Message(
            arbitration_id=0x1,
            data=[self.moteur_state],
            is_extended_id=False
        )
        self.bus.send(frame_to_write)
    def sendMoteurVitesseCAN(self):
        text_to_send = self.edit_vitesse.text()
        if text_to_send.isdigit():
            if int(text_to_send) < 256:
                frame_to_write = can.Message(
                    arbitration_id=0x2,
                    data=[int(text_to_send)],
                    is_extended_id=False
                )
                self.bus.send(frame_to_write)
    def sendAnemoVitesseCAN(self):
        text_to_send = self.minimum_vitesse.text()
        if text_to_send.isdigit():
            if int(text_to_send) < 61:
                frame_to_write = can.Message(
                    arbitration_id=0x3,
                    data=[int(text_to_send)],
                    is_extended_id=False
                )
                self.bus.send(frame_to_write)
    def startMotor(self):
        self.moteur_state = 1
        frame_start = can.Message(
            arbitration_id=0x1,
            data=[self.moteur_state],
            is_extended_id=False
        )
        print(f"[DEBUG] Envoi CAN: Etat moteur = 1 (arbitration_id=0x1)")
        self.bus.send(frame_start)
    def stopMotor(self):
        self.moteur_state = 0
        frame_stop = can.Message(
            arbitration_id=0x1,
            data=[self.moteur_state],
            is_extended_id=False
        )
        print(f"[DEBUG] Envoi CAN: Etat moteur = 0 (arbitration_id=0x1)")
        self.bus.send(frame_stop)
def inverse_byte(byte):
    return ~byte & 0xFF

# ---------------- VL6180 CODE ----------------
class VL6180Dialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.switch_state = 0
        self.moteur_state = 0
        self.setWindowTitle('VL6180X – Dashboard')
        self.setGeometry(420, 220, 540, 560)
        # Fond bleu très clair
        self.setStyleSheet("background: #e3f2fd;")
        from PyQt5.QtGui import QPixmap, QFont
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        # Carte centrale blanche
        card = QWidget()
        card.setStyleSheet("""
            background: #fff;
            border-radius: 28px;
            margin: 32px 32px 18px 32px;
            border: 2px solid #90caf9;
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(22)
        card_layout.setContentsMargins(36, 28, 36, 28)
        # Image stylisée
        vl_img = QLabel()
        vl_img.setAlignment(Qt.AlignCenter)
        vl_img_path = asset_path("vl6180x.png")
        vl_img.setPixmap(QPixmap(vl_img_path).scaled(90, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        vl_img.setStyleSheet("margin-bottom: 8px;")
        card_layout.addWidget(vl_img)
        # Titre moderne
        label = QLabel("VL6180X")
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Segoe UI", 25, QFont.Bold))
        label.setStyleSheet("color: #185a9d; letter-spacing: 2px; margin-bottom: 0px;")
        card_layout.addWidget(label)
        # LCDs et labels
        self.label_lum = QLabel("Intensité lumineuse (LUX)", self)
        self.label_lum.setAlignment(Qt.AlignCenter)
        self.label_lum.setStyleSheet("font-size: 18px; color: #1976d2; font-family: 'Segoe UI'; margin-bottom: 2px;")
        self.lcd_lum = QLCDNumber(self)
        self.lcd_lum.setStyleSheet("background: #fff; color: #1976d2; border: 2px solid #1976d2; border-radius: 10px; margin-bottom: 0px;")
        self.label_temp = QLabel("Température (°C)", self)
        self.label_temp.setAlignment(Qt.AlignCenter)
        self.label_temp.setStyleSheet("font-size: 18px; color: #1976d2; font-family: 'Segoe UI'; margin-bottom: 2px;")
        self.lcd_temp = QLCDNumber(self)
        self.lcd_temp.setStyleSheet("background: #fff; color: #1976d2; border: 2px solid #1976d2; border-radius: 10px; margin-bottom: 0px;")
        self.label_pression = QLabel("Pression (hPa)", self)
        self.label_pression.setAlignment(Qt.AlignCenter)
        self.label_pression.setStyleSheet("font-size: 18px; color: #1976d2; font-family: 'Segoe UI'; margin-bottom: 2px;")
        self.lcd_pression = QLCDNumber(self)
        self.lcd_pression.setStyleSheet("background: #fff; color: #1976d2; border: 2px solid #1976d2; border-radius: 10px; margin-bottom: 0px;")
        self.label_hum = QLabel("Humidité ", self)
        self.label_hum.setAlignment(Qt.AlignCenter)
        self.label_hum.setStyleSheet("font-size: 18px; color: #1976d2; font-family: 'Segoe UI'; margin-bottom: 2px;")
        self.lcd_hum = QLCDNumber(self)
        self.lcd_hum.setStyleSheet("background: #fff; color: #1976d2; border: 2px solid #1976d2; border-radius: 10px; margin-bottom: 0px;")
        self.label_dist = QLabel("Distance (mm)", self)
        self.label_dist.setAlignment(Qt.AlignCenter)
        self.label_dist.setStyleSheet("font-size: 18px; color: #1976d2; font-family: 'Segoe UI'; margin-bottom: 2px;")
        self.lcd_dist = QLCDNumber(self)
        self.lcd_dist.setStyleSheet("background: #fff; color: #1976d2; border: 2px solid #1976d2; border-radius: 10px; margin-bottom: 0px;")
        # Bouton stylé bleu foncé
        btn_style = """
            QPushButton {
                background: #1976d2;
                color: #fff;
                font-size: 16px;
                font-family: 'Segoe UI';
                font-weight: bold;
                border-radius: 12px;
                border: none;
                padding: 10px 0px;
                margin: 8px 0px;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: #1565c0;
                color: #fff;
            }
        """
        self.send_can = QPushButton("Basculer Lumière / Distance")
        self.send_can.setStyleSheet(btn_style)
        self.send_can.clicked.connect(self.sendSwitchStatusCAN)
        # Ajout des widgets à la carte
        card_layout.addWidget(self.label_lum)
        card_layout.addWidget(self.lcd_lum)
        card_layout.addWidget(self.label_temp)
        card_layout.addWidget(self.lcd_temp)
        card_layout.addWidget(self.label_pression)
        card_layout.addWidget(self.lcd_pression)
        card_layout.addWidget(self.label_hum)
        card_layout.addWidget(self.lcd_hum)
        card_layout.addWidget(self.label_dist)
        card_layout.addWidget(self.lcd_dist)
        card_layout.addWidget(self.send_can)
        main_layout.addStretch(1)
        main_layout.addWidget(card, alignment=Qt.AlignCenter)
        main_layout.addStretch(1)
        # Elements Capteur (fonctions inchangées)
        self.bus = can.interface.Bus(channel=f"can{CAN_BUS_NUMBER}", bustype='socketcan')
        self.timer_anemo = QTimer()
        self.timer_anemo.timeout.connect(self.readCanDataAnemo)
        self.timer_anemo.start(1)
    def readCanDataAnemo(self):
        message = self.bus.recv(timeout=0.1)
        if message is not None:
            if message.arbitration_id == 16:
                value = int.from_bytes(message.data, byteorder='big')
                self.lcd_temp.display(value/1000)
            elif message.arbitration_id == 17:
                value = int.from_bytes(message.data, byteorder='big')
                self.lcd_pression.display(value/1000)
            elif message.arbitration_id == 18:
                value = int.from_bytes(message.data, byteorder='big')
                self.lcd_hum.display(value/1000)
            elif message.arbitration_id == 19:
                value = int.from_bytes(message.data, byteorder='big')
                self.lcd_lum.display(value)
            elif message.arbitration_id == 20:
                value = int.from_bytes(message.data, byteorder='big')
                self.lcd_dist.display(value)
    def sendSwitchStatusCAN(self):
        self.switch_state = (self.switch_state + 1) % 2
        frame_to_write = can.Message(
            arbitration_id=0x4,
            data=[self.switch_state],
            is_extended_id=False
        )
        self.bus.send(frame_to_write)
    def sendMoteurStatusCAN(self):
        self.moteur_state = (self.moteur_state + 1) % 2
        frame_to_write = can.Message(
            arbitration_id=0x1,
            data=[self.moteur_state],
            is_extended_id=False
        )
        self.bus.send(frame_to_write)
    def sendMoteurVitesseCAN(self):
        text_to_send = self.edit_vitesse.text()
        if text_to_send.isdigit():
            if int(text_to_send) < 256:
                frame_to_write = can.Message(
                    arbitration_id=0x2,
                    data=[int(text_to_send)],
                    is_extended_id=False
                )
                self.bus.send(frame_to_write)
    def sendAnemoVitesseCAN(self):
        text_to_send = self.minimum_vitesse.text()
        if text_to_send.isdigit():
            if int(text_to_send) < 61:
                frame_to_write = can.Message(
                    arbitration_id=0x3,
                    data=[int(text_to_send)],
                    is_extended_id=False
                )
                self.bus.send(frame_to_write)
    def inverse_byte(byte):
        return ~byte & 0xFF

# ---------------- MPU9250 CODE ----------------
class MPU9250Dialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('MPU9250 – Détails')
        self.setMinimumSize(500, 500)
        self.setStyleSheet("background-color: #f0f4f8;")
        self.list_phi = [0, 0, 0]
        self.list_theta = [0, 0, 0]
        self.list_psi = [0, 0, 0]
        layout = QVBoxLayout()
        # Ajout image MPU9250
        from PyQt5.QtGui import QPixmap
        mpu_img = QLabel()
        mpu_img.setAlignment(Qt.AlignCenter)
        mpu_img.setPixmap(QPixmap(asset_path("mpu9250.png")).scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(mpu_img)
        label = QLabel("Informations Capteur MPU9250")
        label.setStyleSheet("font-size: 26px; font-weight: bold; color: #2c3e50; margin-bottom: 20px;")
        layout.addWidget(label)
        self.setLayout(layout)
        self.lcd_phi = QLCDNumber(self)
        self.lcd_phi.setStyleSheet("background: #eaf6fb; color: #2980b9; border: 2px solid #2980b9; border-radius: 8px;")
        self.label_phi = QLabel("Angle Phi (°)", self)
        self.label_phi.setAlignment(Qt.AlignCenter)
        self.label_phi.setStyleSheet("font-size: 20px; color: #34495e;")
        self.lcd_theta = QLCDNumber(self)
        self.lcd_theta.setStyleSheet("background: #eaf6fb; color: #27ae60; border: 2px solid #27ae60; border-radius: 8px;")
        self.label_theta = QLabel("Angle Theta (°)", self)
        self.label_theta.setAlignment(Qt.AlignCenter)
        self.label_theta.setStyleSheet("font-size: 20px; color: #34495e;")
        self.lcd_psi = QLCDNumber(self)
        self.lcd_psi.setStyleSheet("background: #eaf6fb; color: #e67e22; border: 2px solid #e67e22; border-radius: 8px;")
        self.label_psi = QLabel("Angle Psi (°)", self)
        self.label_psi.setAlignment(Qt.AlignCenter)
        self.label_psi.setStyleSheet("font-size: 20px; color: #34495e;")
        self.cube = cubegl.GLWidget()
        layout.addWidget(self.label_phi)
        layout.addWidget(self.lcd_phi)
        layout.addWidget(self.label_theta)
        layout.addWidget(self.lcd_theta)
        layout.addWidget(self.label_psi)
        layout.addWidget(self.lcd_psi)
        layout.addWidget(self.cube, stretch=1)
        self.bus = can.interface.Bus(channel=f"can{CAN_BUS_NUMBER}", bustype='socketcan')
        self.timer_anemo = QTimer()
        self.timer_anemo.timeout.connect(self.readCanDataAnemo)
        self.timer_anemo.start(1)
    def readCanDataAnemo(self):
        message = self.bus.recv(timeout=0.1)
        if message is not None:
            if message.arbitration_id == 21:
                value = int.from_bytes(message.data, byteorder='big')
                self.list_phi.insert(0, value / 10)
                self.list_phi.pop()
                self.lcd_phi.display((self.list_phi[0] + self.list_phi[1] + self.list_phi[2]) / 3)
                self.cube.setRot((self.list_phi[0] + self.list_phi[1] + self.list_phi[2]) / 3)
            elif message.arbitration_id == 22:
                value = int.from_bytes(message.data, byteorder='big')
                self.list_theta.insert(0, value / 10)
                self.list_theta.pop()
                self.lcd_theta.display((self.list_theta[0] + self.list_theta[1] + self.list_theta[2]) / 3)
                self.cube.setRotY((self.list_theta[0] + self.list_theta[1] + self.list_theta[2]) / 3)
            elif message.arbitration_id == 23:
                value = int.from_bytes(message.data, byteorder='big')
                self.list_psi.insert(0, value / 10)
                self.list_psi.pop()
                self.lcd_psi.display((self.list_psi[0] + self.list_psi[1] + self.list_psi[2]) / 3)
                self.cube.setRotZ((self.list_psi[0] + self.list_psi[1] + self.list_psi[2]) / 3)
            self.cube.updateGL()
    def sendSwitchStatusCAN(self):
        self.switch_state = (self.switch_state + 1) % 2
        frame_to_write = can.Message(
            arbitration_id=0x4,
            data=[self.switch_state],
            is_extended_id=False
        )
        self.bus.send(frame_to_write)
    def sendMoteurStatusCAN(self):
        self.moteur_state = (self.moteur_state + 1) % 2
        frame_to_write = can.Message(
            arbitration_id=0x1,
            data=[self.moteur_state],
            is_extended_id=False
        )
        self.bus.send(frame_to_write)
    def sendMoteurVitesseCAN(self):
        text_to_send = self.edit_vitesse.text()
        if text_to_send.isdigit():
            if int(text_to_send) < 256:
                frame_to_write = can.Message(
                    arbitration_id=0x2,
                    data=[int(text_to_send)],
                    is_extended_id=False
                )
                self.bus.send(frame_to_write)
    def sendAnemoVitesseCAN(self):
        text_to_send = self.minimum_vitesse.text()
        if text_to_send.isdigit():
            if int(text_to_send) < 61:
                frame_to_write = can.Message(
                    arbitration_id=0x3,
                    data=[int(text_to_send)],
                    is_extended_id=False
                )
                self.bus.send(frame_to_write)
    def inverse_byte(byte):
        return ~byte & 0xFF

# ---------------- MAIN WINDOW (IHM) CODE ----------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Tableau de bord – Capteurs')
        self.setGeometry(100, 100, 700, 600)
        self.setStyleSheet("background: qradialgradient(cx:0.5, cy:0.3, radius:1.2, fx:0.5, fy:0.3, stop:0 #fafdff, stop:1 #b8c6db);")
        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        layout = QVBoxLayout(centralWidget)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        # Carte centrale
        from PyQt5.QtGui import QPixmap, QFont
        card = QWidget()
        card.setStyleSheet("background: white; border-radius: 24px; margin: 40px 80px 20px 80px;")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(18)
        card_layout.setContentsMargins(40, 30, 40, 30)
        # Titre
        title = QLabel("BUS CAN")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 32, QFont.Bold))
        title.setStyleSheet("color: #1a237e; letter-spacing: 2px; margin-bottom: 0px;")
        card_layout.addWidget(title)
        # Welcome
        welcome = QLabel("Bienvenue sur le Dashboard BUS CAN !")
        welcome.setAlignment(Qt.AlignCenter)
        welcome.setStyleSheet("font-size: 22px; color: #1976d2; margin-bottom: 0px;")
        card_layout.addWidget(welcome)
        # Noms équipe
        team = QLabel("Projet réalisé par : Lara, Tarek, Ahmad, Bilal")
        team.setAlignment(Qt.AlignCenter)
        team.setStyleSheet("font-size: 15px; color: #374151; margin-bottom: 8px;")
        card_layout.addWidget(team)
        # Image centrale
        home_img = QLabel()
        home_img.setAlignment(Qt.AlignCenter)
        home_img_path = asset_path("home_page.png")
        home_img.setPixmap(QPixmap(home_img_path).scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        home_img.setStyleSheet("margin: 10px auto 10px auto;")
        card_layout.addWidget(home_img)
        # Boutons stylés
        btn_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1976d2, stop:1 #64b5f6);
                color: white;
                font-size: 20px;
                font-weight: bold;
                border-radius: 14px;
                padding: 16px 0px;
                margin: 8px 0px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #64b5f6, stop:1 #1976d2);
                color: #fffde7;
            }
        """
        vl6180_button = QPushButton('Capteur VL6180X')
        vl6180_button.setStyleSheet(btn_style)
        mpu9250_button = QPushButton('Capteur MPU9250')
        mpu9250_button.setStyleSheet(btn_style)
        anemo_button = QPushButton('Anémomètre')
        anemo_button.setStyleSheet(btn_style)
        card_layout.addWidget(vl6180_button)
        card_layout.addWidget(mpu9250_button)
        card_layout.addWidget(anemo_button)
        vl6180_button.clicked.connect(self.open_vl6180_dialog)
        mpu9250_button.clicked.connect(self.open_mpu9250_dialog)
        anemo_button.clicked.connect(self.open_anemo_dialog)
        layout.addStretch(1)
        layout.addWidget(card, alignment=Qt.AlignCenter)
        layout.addStretch(1)
        # Footer
        footer = QLabel("© 2026 BUS CAN Project – Tous droits réservés")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: #90a4ae; font-size: 13px; margin-bottom: 8px;")
        layout.addWidget(footer)
    def open_vl6180_dialog(self):
        dialog = VL6180Dialog(self)
        dialog.exec_()
    def open_mpu9250_dialog(self):
        dialog = MPU9250Dialog(self)
        dialog.exec_()
    def open_anemo_dialog(self):
        dialog = ANEMODialog(self)
        dialog.exec_()
def main():
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())
if __name__ == "__main__":
    main()
