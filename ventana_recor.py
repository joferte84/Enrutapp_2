from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtCore import Qt


class VentanaRecordatorio(QWidget):
    def __init__(self, mensaje, parent=None):
        """
    Inicializa la ventana de recordatorio con un mensaje específico.
    Configura la ventana para que sea flotante, translúcida y centrada en la pantalla.
    Args:
        mensaje (str): Mensaje a mostrar en la ventana.
        parent (QWidget, opcional): Widget padre, si aplica.
    """
        super().__init__(parent)

        # Configuración de la ventana
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)  
        self.setFixedSize(500, 250)
        self.setStyleSheet("""
            background-color: rgba(50, 50, 50, 180);
            color: white;
            border-radius: 10px;
            font-size: 16px;
            padding: 10px;
        """)

        # Layout y contenido
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        # Etiqueta con el mensaje
        label = QLabel(mensaje, self)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 16px; padding: 10px;")
        layout.addWidget(label)

        # Botón para cerrar la ventana
        close_button = QPushButton("Cerrar", self)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #04a4d3;
                color: white;
                font-size: 14px;
                border-radius: 10px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #046d94;
            }
        """)
        close_button.clicked.connect(self.cerrar_ventana)
        layout.addWidget(close_button)

        # Centrar ventana en la pantalla
        self.center_on_screen()

    def cerrar_ventana(self):
        """
    Cierra explícitamente la ventana de recordatorio.
    """
        self.close()

    def center_on_screen(self):
        """
    Centra la ventana de recordatorio en el centro de la pantalla principal.
    """
        screen_geometry = self.screen().geometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)
