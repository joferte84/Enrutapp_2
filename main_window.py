#modulos/main_window.py
import os

from PyQt5.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QMessageBox, QDialog
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap

from modulos.rutas_urgentes import RutasUrgentesWindow
from modulos.buscar_hueco import BuscarHueco
from modulos.tecnicos import BuscarTecnicoWindow
from modulos.actualizar_tecnicos import ActualizarTecnicos
from modulos.logger_config import logger, get_data_dir
from modulos.loader import LoaderWidget

from modulos.ordenes_cercanas import OrdenesCercanas
from modulos.ventana_recor import VentanaRecordatorio


class LoaderDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cargando")
        self.resize(150, 150)
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint)

        layout = QVBoxLayout(self)
        self.loader = LoaderWidget()
        layout.addWidget(self.loader)
        label = QLabel("Cargando, espere...")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        self.setWindowModality(Qt.ApplicationModal)

    def start_loading(self, duration=3000, callback=None):
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: (self.accept(), callback() if callback else None))
        timer.start(duration)
        self.exec_()

class MainWindow(QMainWindow):
    def __init__(self, nombre="Usuario", apellido=""):
        super().__init__()
        self.nombre = nombre
        self.apellido = apellido

        self.initUI()
        self.init_timer()
        self.recordatorio_activo = None 

    def initUI(self):
        """
    Inicializa la interfaz gráfica principal de la aplicación, incluyendo el logo,
    los botones de navegación, y la estructura del layout principal.
    """
        self.setWindowTitle("ENRUTAPP")
        self.setGeometry(125, 100, 1600, 900)

        # Logo de la aplicación
        try:

            # Ruta de la imagen
            logo_path = os.path.join(get_data_dir(), "logo_contact_center-100.png")

            logo_label = QLabel(self)
            pixmap = QPixmap(logo_path)

            if pixmap.isNull():
                raise FileNotFoundError(f"No se pudo cargar la imagen desde {logo_path}")
            else:
                pixmap = pixmap.scaled(400, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                logo_label.setPixmap(pixmap)
                logo_label.setAlignment(Qt.AlignCenter)

        except Exception as e:
            logger.debug(f"[DEBUG] Error al cargar la imagen: {e}")
            logo_label = QLabel("Error: No se pudo cargar el logo")
            logo_label.setAlignment(Qt.AlignCenter)

        # Contenedor principal
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        # Layout principal
        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)

        # Contenedor dinámico para los widgets de los módulos
        self.content_area = QVBoxLayout()

        # Botones
        ordenes_cercanas_btn = QPushButton("Órdenes Cercanas")        
        cargar_rutas_btn = QPushButton("Órdenes Prioritarias")
        filtrar_zonas_btn = QPushButton("Buscar Hueco")
        mostrar_rutas_btn = QPushButton("Mostrar Rutas")
        # actualizar_tecnicos_btn = QPushButton("Actualizar Técnicos")

    # Aplicar estilo a los botones  
        button_style = """
            QPushButton {
                font-size: 18px;   /* Tamaño de la fuente */
                font-weight: bold; /* Fuente en negrita */
                padding: 15px;     /* Espaciado interno */
                min-height: 30px;  /* Altura mínima */
                border-radius: 5px; /* Bordes redondeados */
                background-color: #046d94; /* Color de fondo azul */
                color: white;      /* Color del texto */
            }
            QPushButton:hover {
                background-color: #04a4d3; /* Azul más claro al pasar el mouse */
            }
            QPushButton:pressed {
                background-color: #046d94; /* Azul más oscuro al presionar */
            }
        """

        # Estilo del botón pequeño
        small_button_style = """
            QPushButton {
                font-size: 16px;       /* Tamaño de fuente más pequeño */
                font-weight: bold;   /* Fuente no en negrita */
                padding: 10px;         /* Espaciado interno */
                min-height: 40px;      /* Altura mínima */
                min-width: 150px;      /* Ancho mínimo */
                max-width: 160px;      /* Ancho máximo */
                border-radius: 5px;    /* Bordes redondeados */
                background-color: #003060;  /* Color naranja */
                color: white;          /* Color del texto */
            }
            QPushButton:hover {
                background-color: #68BBE3;  /* Color más oscuro al pasar el mouse */
                color: white;
            }
            QPushButton:pressed {
                background-color: #41729f;  /* Color más oscuro al presionar */
                color: white;
            }
        """

        ordenes_cercanas_btn.setStyleSheet(button_style)
        cargar_rutas_btn.setStyleSheet(button_style)
        filtrar_zonas_btn.setStyleSheet(button_style)
        mostrar_rutas_btn.setStyleSheet(button_style)
        # actualizar_tecnicos_btn.setStyleSheet(small_button_style)

        # Conectar botones a métodos
        ordenes_cercanas_btn.clicked.connect(self.show_ordenes_cercanas)
        cargar_rutas_btn.clicked.connect(self.show_rutas_urgentes)
        filtrar_zonas_btn.clicked.connect(self.show_buscar_hueco)
        mostrar_rutas_btn.clicked.connect(self.show_buscar_tecnico)
        # actualizar_tecnicos_btn.clicked.connect(self.run_actualizar_tecnicos)

        # Layout de botones
        button_layout = QHBoxLayout()
        button_layout.addWidget(ordenes_cercanas_btn)
        button_layout.addWidget(cargar_rutas_btn)
        button_layout.addWidget(filtrar_zonas_btn)
        button_layout.addWidget(mostrar_rutas_btn)
        # button_layout.addWidget(actualizar_tecnicos_btn)

        # Añadir widgets al layout principal
        self.main_layout.addWidget(logo_label)
        self.main_layout.addLayout(button_layout)
        self.main_layout.addLayout(self.content_area)

    def open_login(self):
        """
    Abre la ventana de login y la muestra al usuario.
    """
        # Importación local para evitar el ciclo
        from modulos.login import LoginWindow
        self.login_window = LoginWindow()
        self.login_window.show()

    # Órdenes Cercanas
    def show_ordenes_cercanas(self):
        self.clear_content_area()
        loader = LoaderDialog()
        try:
            loader.start_loading(callback=lambda: self.load_ordenes_cercanas())
        except Exception as e:
            self.show_error_message("Error", f"Error al cargar Órdenes Cercanas: {str(e)}")

    def load_ordenes_cercanas(self):
        try:
            widget = OrdenesCercanas()
            self.content_area.addWidget(widget)
        except Exception as e:
            self.show_error_message("Error", f"Error al mostrar Órdenes Cercanas: {str(e)}")

    # Rutas Urgentes
    def show_rutas_urgentes(self):
        self.clear_content_area()
        loader = LoaderDialog()
        try:
            loader.start_loading(callback=lambda: self.load_rutas_urgentes())
        except Exception as e:
            self.show_error_message("Error", f"Error al cargar Rutas Urgentes: {str(e)}")

    def load_rutas_urgentes(self):
        try:
            widget = RutasUrgentesWindow()
            self.content_area.addWidget(widget)
        except Exception as e:
            self.show_error_message("Error", f"Error al mostrar Rutas Urgentes: {str(e)}")

    # Buscar Hueco
    def show_buscar_hueco(self):
        self.clear_content_area()
        loader = LoaderDialog()
        try:
            loader.start_loading(callback=lambda: self.load_buscar_hueco())
        except Exception as e:
            self.show_error_message("Error", "Error al cargar Búsqueda de Hueco")

    def load_buscar_hueco(self):
        try:
            widget = BuscarHueco()
            self.content_area.addWidget(widget)
        except Exception as e:
            self.show_error_message("Error", "Error al mostrar Búsqueda de Hueco")

    # Buscar Técnico
    def show_buscar_tecnico(self):
        self.clear_content_area()
        loader = LoaderDialog()
        try:
            loader.start_loading(callback=lambda: self.load_buscar_tecnico())
        except Exception as e:
            self.show_error_message("Error", "Error al cargar Búsqueda de Técnico")

    def load_buscar_tecnico(self):
        try:
            widget = BuscarTecnicoWindow()
            self.content_area.addWidget(widget)
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error en load_buscar_tecnico: {e}\n{error_trace}")
            self.show_error_message("Error", "Error al mostrar Búsqueda de Técnico")

    def run_actualizar_tecnicos(self):
        """
    Ejecuta la funcionalidad de actualización de técnicos mediante un scraper,
    utilizando las credenciales cargadas desde un archivo JSON.
    Muestra mensajes de éxito o error dependiendo del resultado.
    """
        """Ejecuta la funcionalidad para actualizar técnicos."""
        download_path = os.path.join(os.path.expanduser("~"), "Downloads")

        try:
            # Cargar credenciales del archivo JSON desde login.py
            from modulos.utils import cargar_credenciales
            credenciales = cargar_credenciales()
            
            email = list(credenciales.keys())[0]
            password = credenciales[email]

            # Crear una instancia del scraper con las credenciales cargadas
            scraper = ActualizarTecnicos(email=email, password=password, download_path=download_path)

            # Descargar el archivo Excel
            resultado = scraper.descargar_excel()
            QMessageBox.information(self, "Éxito", resultado)

        except FileNotFoundError as e:
            QMessageBox.warning(self, "Error", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo actualizar: {e}")


    def clear_content_area(self):
        """
    Limpia todos los widgets del área de contenido de la ventana principal.
    """
        for i in reversed(range(self.content_area.count())):
            widget_to_remove = self.content_area.itemAt(i).widget()
            if widget_to_remove:
                widget_to_remove.deleteLater()

    def show_error_message(self, title, message):
        """
    Muestra un cuadro de diálogo con un mensaje de error.
    Args:
        title (str): Título del cuadro de diálogo.
        message (str): Mensaje del error.
    """
        error_dialog = QMessageBox(self)
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setWindowTitle(title)
        error_dialog.setText(message)
        error_dialog.exec_()

    def init_timer(self):
        """
    Inicializa un temporizador para mostrar recordatorios al usuario en intervalos regulares.
    """
        self.timer = QTimer(self)
        self.timer.setInterval(90 * 60 * 1000)  # Intervalo: 90 minutos en milisegundos
        self.timer.timeout.connect(self.mostrar_recordatorio)  
        self.timer.start()  # Inicia el temporizador

    def mostrar_recordatorio(self):
        """
    Muestra una ventana flotante con un mensaje recordatorio al usuario.
    Si ya hay un recordatorio activo, no muestra uno nuevo.
    """
        if self.recordatorio_activo and not self.recordatorio_activo.isHidden():
            return
        
        mensaje = (
        "⏰ ¡Recordatorio importante! \n\n"
        "Por favor, descarga los datos del PME y haz clic en 'Buscar hueco' "
        "para actualizar las rutas."
        )        
        ventana = VentanaRecordatorio(mensaje, self)
        ventana.show()
