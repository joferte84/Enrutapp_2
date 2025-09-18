# modulos/login.py
import json
import os
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QLineEdit, QPushButton, QMessageBox, QCheckBox, QDialog
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt, pyqtSignal
from modulos.utils import cargar_credenciales, guardar_credenciales
from modulos.logger_config import logger, get_data_dir

DATA_DIR = get_data_dir()
CONFIG_PATH = os.path.join(DATA_DIR, "credenciales.json")


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.credenciales_guardadas = cargar_credenciales(CONFIG_PATH)
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Login - ENRUTAPP")
        self.setGeometry(300, 300, 500, 400)

        # Crear logo
        self.logo_label = QLabel(self)
        logo_path = os.path.join(DATA_DIR, "logo_contact_center-100.png")
        pixmap = QPixmap(logo_path)
        if pixmap.isNull():
            self.logo_label.setText("Error: No se pudo cargar el logo")
            self.logo_label.setAlignment(Qt.AlignCenter)
        else:
            pixmap = pixmap.scaled(300, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_label.setPixmap(pixmap)
            self.logo_label.setAlignment(Qt.AlignCenter)

        # Crear widgets
        self.user_label = QLabel('Correo:', self)
        self.password_label = QLabel('Contraseña:', self)
        self.user_input = QLineEdit(self)
        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.Password)
        self.login_button = QPushButton('Iniciar sesión', self)

        self.show_password_checkbox = QCheckBox("Mostrar contraseña", self)
        self.show_password_checkbox.stateChanged.connect(self.toggle_password_visibility)

        # Estilo para las etiquetas y campos de texto
        label_style = "font-size: 16px; font-weight: bold; color: #046d94;"
        input_style = "font-size: 16px; padding: 5px;"
        self.user_label.setStyleSheet(label_style)
        self.password_label.setStyleSheet(label_style)
        self.user_input.setStyleSheet(input_style)
        self.password_input.setStyleSheet(input_style)

        # Estilo del botón
        button_style = """
            QPushButton {
                font-size: 18px;
                font-weight: bold;
                padding: 15px;
                min-height: 30px;
                border-radius: 5px;
                background-color: #046d94;
                color: white;
            }
            QPushButton:hover {
                background-color: #04a4d3;
            }
            QPushButton:pressed {
                background-color: #046d94;
            }
        """
        self.login_button.setStyleSheet(button_style)

        # Conectar botones
        self.login_button.clicked.connect(self.login)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.logo_label)
        layout.addWidget(self.user_label)
        layout.addWidget(self.user_input)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)
        layout.addWidget(self.show_password_checkbox)
        layout.addWidget(self.login_button)
        self.setLayout(layout)

        registro_label = QLabel("¿Eres nuevo? <a href='#'>Regístrate aquí</a>")
        registro_label.setOpenExternalLinks(False)
        registro_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        registro_label.setStyleSheet("font-size: 14px; color: blue;")
        registro_label.linkActivated.connect(self.abrir_registro)
        layout.addWidget(registro_label)

    def abrir_registro(self):
        self.registro_window = RegistroWindow()
        self.registro_window.registrado.connect(self.reload_credentials)
        self.registro_window.exec_()

    def reload_credentials(self):
        self.credenciales_guardadas = cargar_credenciales(CONFIG_PATH)

    def toggle_password_visibility(self):
        self.password_input.setEchoMode(QLineEdit.Normal if self.show_password_checkbox.isChecked() else QLineEdit.Password)

    def login(self):
        email = self.user_input.text()
        password = self.password_input.text()

        if not email or not password:
            QMessageBox.warning(self, 'Error', 'Por favor, ingrese correo y contraseña.')
            return

        if hasattr(self, 'credenciales_guardadas') and email in self.credenciales_guardadas:
            if self.credenciales_guardadas[email] == password:
                logger.info(f"Inicio de sesión exitoso: {email}")
                self.openMainWindow(email)
            else:
                QMessageBox.critical(self, 'Error', 'Correo o contraseña incorrectos.')
        else:
            QMessageBox.critical(self, 'Error', 'Error: No se encontraron credenciales almacenadas.')

    def openMainWindow(self, email):
        from modulos.main_window import MainWindow
        self.close()
        self.main_window = MainWindow(nombre=email.split("@")[0].capitalize(), apellido="")
        self.main_window.show()

class RegistroWindow(QDialog):
    registrado = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Registro")
        self.setGeometry(400, 300, 400, 300)
        layout = QVBoxLayout()

        input_style = "font-size: 16px; padding: 5px;"

        title_label = QLabel("Registro", self)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #046d94;")
        layout.addWidget(title_label)

        self.email_input = QLineEdit(self)
        self.email_input.setPlaceholderText("Correo corporativo")
        self.email_input.setStyleSheet(input_style)
        self.password_input = QLineEdit(self)
        self.password_input.setPlaceholderText("Contraseña")
        self.password_input.setStyleSheet(input_style)
        self.password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input = QLineEdit(self)
        self.confirm_password_input.setPlaceholderText("Confirmar contraseña")
        self.confirm_password_input.setStyleSheet(input_style)
        self.confirm_password_input.setEchoMode(QLineEdit.Password)

        self.show_password_checkbox = QCheckBox("Mostrar contraseñas", self)
        self.show_password_checkbox.stateChanged.connect(self.toggle_password_visibility)

        self.register_button = QPushButton("Registrar", self)

        # Estilo del botón
        button_style = """
            QPushButton {
                font-size: 18px;
                font-weight: bold;
                padding: 15px;
                min-height: 30px;
                border-radius: 5px;
                background-color: #046d94;
                color: white;
            }
            QPushButton:hover {
                background-color: #04a4d3;
            }
            QPushButton:pressed {
                background-color: #046d94;
            }
        """
        self.register_button.setStyleSheet(button_style)

        self.register_button.clicked.connect(self.registrar)

        layout.addWidget(self.email_input)
        layout.addWidget(self.password_input)
        layout.addWidget(self.confirm_password_input)
        layout.addWidget(self.show_password_checkbox)
        layout.addWidget(self.register_button)
        self.setLayout(layout)

    def toggle_password_visibility(self):
        mode = QLineEdit.Normal if self.show_password_checkbox.isChecked() else QLineEdit.Password
        self.password_input.setEchoMode(mode)
        self.confirm_password_input.setEchoMode(mode)

    def registrar(self):
        email = self.email_input.text()
        if not email.endswith('@agioglobal.es'):
            QMessageBox.warning(self, "Error", "El correo debe pertenecer al dominio @agioglobal.es.")
            return
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()

        if not email or not password or not confirm_password:
            QMessageBox.warning(self, "Error", "Todos los campos son obligatorios.")
            return

        if password != confirm_password:
            QMessageBox.warning(self, "Error", "Las contraseñas no coinciden.")
            return

        credenciales = cargar_credenciales(CONFIG_PATH)
        if email in credenciales:
            QMessageBox.warning(self, "Error", "Este correo ya está registrado.")
            return

        guardar_credenciales(email, password, CONFIG_PATH)
        QMessageBox.information(self, "Éxito", "Registro exitoso.")
        self.registrado.emit()
        self.accept()
