# modulos/rutas_urgentes.py
import pandas as pd
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QScrollArea
from PyQt5.QtCore import Qt
from datetime import time

from modulos.utils import (obtener_lat_lon_de_direccion, calcular_distancia_haversine, 
                           cargar_configuracion, formatear_codigo_postal)

from modulos.logger_config import logger
from modulos.api_manager import APIManager

api_manager = APIManager()

class RutasUrgentesWindow(QWidget):
    def __init__(self):
        """
    Inicializa la ventana de órdenes de servicio urgentes, configurando la interfaz gráfica y variables principales.
    """
        super().__init__()
        self.init_ui()
        self.fecha_actual = None
        self.rutas_tecnicos = None
        self.duracion_nueva_visita = None
        self.rutas_tecnicos_local = None

    def init_ui(self):
        """
    Configura la interfaz gráfica de usuario, incluyendo campos de entrada, botones de búsqueda,
    barra de desplazamiento para resultados, y botones de navegación para cambiar entre días.
    """
        self.setWindowTitle("Órdenes de Servicio Urgentes")
        self.resize(800, 600)

        # Layout principal
        self.layout = QVBoxLayout()

        # Layout para la entrada de código postal y duración
        input_layout = QHBoxLayout()

        # Añadir un espaciador al principio para alinear a la derecha
        input_layout.addStretch()

        BUTTON_STYLE = """
            QPushButton {
                background-color: #04a4d3;
                color: white;
                font-size: 16px;
                border-radius: 5px; /* Bordes redondeados de 5px */
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #049cc4; /* Cambia ligeramente el color al pasar el ratón */
            }
            QPushButton:pressed {
                background-color: #046d94; /* Cambia el color al hacer clic */
            }
            """


        self.cp_input = QLineEdit(self)
        self.cp_input.setPlaceholderText("Ejemplo: 28001 (Madrid)")
        self.cp_input.setFixedSize(400, 40)
        self.cp_input.setStyleSheet("font-size: 16px; border-radius: 5px; padding: 5px; border: 2px solid #046d94;")

        self.duracion_input = QLineEdit(self)
        self.duracion_input.setPlaceholderText("Duración de la visita en horas (ej. 1.5)")
        self.duracion_input.setFixedSize(400, 40)
        self.duracion_input.setStyleSheet("font-size: 16px; border-radius: 5px; padding: 5px; border: 2px solid #046d94;")

        # Botón para buscar órdenes urgentes
        buscar_button = QPushButton("Buscar", self)
        buscar_button.setFixedSize(250, 40)
        buscar_button.setStyleSheet(BUTTON_STYLE)
        buscar_button.clicked.connect(self.on_buscar_click)

        input_layout.addWidget(self.cp_input)
        input_layout.addWidget(self.duracion_input)
        input_layout.addWidget(buscar_button)

        self.layout.addLayout(input_layout)

        # Layout para los botones de cambio de día
        dia_layout = QHBoxLayout()

        # Botón de día anterior
        self.dia_anterior_button = QPushButton("Buscar en el día Anterior", self)
        self.dia_anterior_button.setFixedSize(250, 40)
        self.dia_anterior_button.setStyleSheet(BUTTON_STYLE)
        self.dia_anterior_button.clicked.connect(self.on_dia_anterior_click)

        # Botón de día siguiente
        self.siguiente_dia_button = QPushButton("Buscar en el día Siguiente", self)
        self.siguiente_dia_button.setFixedSize(250, 40)
        self.siguiente_dia_button.setStyleSheet(BUTTON_STYLE)
        self.siguiente_dia_button.clicked.connect(self.on_siguiente_dia_click)

        # Añadir los botones al layout
        dia_layout.addWidget(self.dia_anterior_button)
        dia_layout.addWidget(self.siguiente_dia_button)

        # Alinear los botones al centro
        dia_layout.setAlignment(Qt.AlignCenter)

        self.layout.addLayout(dia_layout)

        # Área de desplazamiento para los resultados
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setStyleSheet("background-color: white; border: none;")
        self.scroll_area.setWidgetResizable(True)

        # Contenedor para los resultados
        self.result_container = QWidget()
        self.result_container.setStyleSheet("background-color: white;")
        self.result_layout = QVBoxLayout(self.result_container)
        self.scroll_area.setWidget(self.result_container)

        self.layout.addWidget(self.scroll_area)

        # Etiqueta de estado para mensajes
        self.status_label = QLabel(self)
        self.status_label.setStyleSheet("color: black; font-size: 12px;")
        self.layout.addWidget(self.status_label)

        # Asignar el layout principal
        self.setLayout(self.layout)

            
    def reset_result_area(self):
        """
    Limpia el área de resultados eliminando todos los widgets existentes.
    """
        while self.result_layout.count():
            item = self.result_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def on_buscar_click(self):
        """
    Maneja el evento de clic en el botón "Buscar", validando los campos de entrada, 
    estableciendo una duración por defecto si es necesario, y ejecutando la búsqueda de rutas urgentes.
    """
        cp_usuario = self.cp_input.text().strip()
        duracion_texto = self.duracion_input.text().strip()

        # Si el campo de duración está vacío, asignar un valor por defecto
        if not duracion_texto:
            duracion_texto = "1"  # Duración por defecto en horas

        # Intentar convertir la duración a un número flotante
        try:
            self.duracion_nueva_visita = float(duracion_texto.replace(',', '.'))
        except ValueError:
            self.status_label.setText("Por favor, introduce una duración válida en horas.")
            self.status_label.setStyleSheet("color: red;")
            return

        logger.info(f"Búsqueda de 'órdenes urgentes' iniciada para CP: {cp_usuario} con duración {self.duracion_nueva_visita} horas.")


        # Limpiar mensaje de error si los campos están completos y válidos
        self.status_label.setText("")
        self.buscar_rutas_urgentes(cp_usuario)

    def on_siguiente_dia_click(self):
        """
    Cambia a la búsqueda de rutas para el día siguiente basado en la fecha actual y realiza la búsqueda.
    """
        if self.fecha_actual is not None:
            self.fecha_actual += pd.Timedelta(days=1)
            self.buscar_rutas_para_fecha(self.fecha_actual)

    def on_dia_anterior_click(self):
        """
    Cambia a la búsqueda de rutas para el día anterior basado en la fecha actual y realiza la búsqueda.
    """
        if self.fecha_actual is not None:
            self.fecha_actual -= pd.Timedelta(days=1)
            self.buscar_rutas_para_fecha(self.fecha_actual)

    def buscar_rutas_urgentes(self, cp_usuario):
        """
    Realiza la búsqueda de rutas urgentes para un código postal ingresado, 
    filtra las rutas según la distancia máxima permitida, y las organiza por fecha y distancia.
    Args:
        cp_usuario (str): Código postal ingresado por el usuario.
    """
        configuracion = cargar_configuracion()

        archivo_excel = configuracion['archivo_excel']
        archivo_codigos_postales = configuracion['archivo_codigos_postales']

        self.status_label.setText("Cargando datos de técnicos...")
        self.rutas_tecnicos = self.obtener_rutas_tecnicos(archivo_excel)
        df_codigos_postales = pd.read_excel(archivo_codigos_postales)

        cp_usuario = formatear_codigo_postal(cp_usuario)
        df_codigos_postales['codigo_postal'] = df_codigos_postales['codigo_postal'].apply(formatear_codigo_postal)

        lat_usuario, lon_usuario = obtener_lat_lon_de_direccion(cp_usuario, df_codigos_postales)
        if lat_usuario is None or lon_usuario is None:
            logger.warning(f"Código postal no encontrado: {cp_usuario}")
            self.status_label.setText("Código postal no encontrado.")
            self.status_label.setStyleSheet("color: red;")
            return

        # Procesar Res_Label para quedarse solo con la parte izquierda del guion bajo
        self.rutas_tecnicos['Res_Label'] = self.rutas_tecnicos['Res_Label'].str.split('_').str[0]

        self.rutas_tecnicos = self.rutas_tecnicos.dropna(subset=['Latitud', 'Longitud'])
        self.rutas_tecnicos = self.rutas_tecnicos[~self.rutas_tecnicos['Res_Label'].str.startswith('Pendiente RECUR')]

        # Calcular la distancia al código postal introducido
        self.rutas_tecnicos['Distancia_lat_long'] = self.rutas_tecnicos.apply(
            lambda x: calcular_distancia_haversine(lat_usuario, lon_usuario, x['Latitud'], x['Longitud'])
            if pd.notna(x['Latitud']) and pd.notna(x['Longitud']) else None,
            axis=1
        )

        # Eliminar filas con distancias no válidas y ordenar por distancia
        self.rutas_tecnicos = self.rutas_tecnicos.dropna(subset=['Distancia_lat_long']).sort_values(by=['Distancia_lat_long']).reset_index(drop=True)

        # Filtrar órdenes para que solo se incluyan las que estén dentro de una distancia máxima permitida (por ejemplo, 100 km)
        distancia_maxima_permitida = 100  # Puedes ajustar este valor según sea necesario
        self.rutas_tecnicos = self.rutas_tecnicos[self.rutas_tecnicos['Distancia_lat_long'] <= distancia_maxima_permitida]

        # Verificar si hay órdenes disponibles después del filtrado
        if self.rutas_tecnicos.empty:
            self.status_label.setText("No se encontraron órdenes de servicio dentro de la distancia máxima.")
            self.status_label.setStyleSheet("color: red;")
            return

        # Copiar el DataFrame filtrado
        self.rutas_tecnicos_local = self.rutas_tecnicos.copy()

        # Continuar con el proceso si hay fechas de inicio en los datos
        if 'FechaHoraInicio' in self.rutas_tecnicos.columns:
            self.fecha_actual = self.rutas_tecnicos['FechaHoraInicio'].min().date()
            self.buscar_rutas_para_fecha(self.fecha_actual)
        else:
            self.status_label.setText("Error: No se encontraron fechas de inicio en los datos de técnicos.")
            self.status_label.setStyleSheet("color: red;")

    def buscar_rutas_para_fecha(self, fecha):
        """
    Filtra y muestra las rutas urgentes para una fecha específica, organizadas por distancia y horario de inicio.
    Args:
        fecha (datetime.date): Fecha para buscar rutas urgentes.
    """
        rutas_tecnicos_dia = self.rutas_tecnicos_local[self.rutas_tecnicos_local['FechaHoraInicio'].dt.date == fecha]
        if rutas_tecnicos_dia.empty:
            self.status_label.setText(f"No se encontraron técnicos para la fecha: {fecha.strftime('%d-%m-%Y')}.")
            self.status_label.setStyleSheet("color: red;")
            return

        rutas_tecnicos_dia = rutas_tecnicos_dia.sort_values(by=['Distancia_lat_long', 'FechaHoraInicio']).head(3)

        self.reset_result_area()  # Limpia el área de resultados antes de agregar nuevos datos

        # Mostrar estadísticas directamente para cada técnico
        for _, row in rutas_tecnicos_dia.iterrows():
            self.mostrar_estadisticas_tecnico(row)

        self.status_label.setText("Órdenes cercanas encontradas.")
        self.status_label.setStyleSheet("color: green;")


    def obtener_rutas_tecnicos(self, archivo_excel):
        """
    Carga las rutas de los técnicos desde un archivo Excel, combinándolas con coordenadas geográficas,
    y calcula los horarios de inicio y fin para cada orden de servicio.
    Args:
        archivo_excel (str): Ruta del archivo Excel que contiene los datos de las rutas.
    Returns:
        pd.DataFrame: DataFrame con las rutas de técnicos procesadas.
    """
        df = pd.read_excel(archivo_excel)
        df['codigo_postal'] = df['Evt_PROVINCIA'].str.split('-', expand=True)[0].str.strip()
        df['codigo_postal'] = df['codigo_postal'].apply(formatear_codigo_postal)

        archivo_codigos_postales = cargar_configuracion()['archivo_codigos_postales']
        df_codigos_postales = pd.read_excel(archivo_codigos_postales)
        df_codigos_postales['codigo_postal'] = df_codigos_postales['codigo_postal'].apply(formatear_codigo_postal)
        df = df.merge(df_codigos_postales, on='codigo_postal', how='left')

        df['Dat_StartHour'] = df['Dat_StartHour'].apply(lambda x: x if isinstance(x, str) else x.strftime('%H:%M:%S'))
        df['FechaHoraInicio'] = pd.to_datetime(df['Dat_StartDate'].astype(str) + ' ' + df['Dat_StartHour'], errors='coerce')
        df['FechaHoraFin'] = df['FechaHoraInicio'] + pd.to_timedelta(df['Dat_Hours'], unit='h')

        return df

    def agregar_botones_estadisticas(self, rutas):
        """
    Genera botones dinámicos para mostrar las estadísticas de cada técnico disponible en las rutas.
    Args:
        rutas (pd.DataFrame): DataFrame que contiene las rutas a mostrar en los botones.
    """
        for i in reversed(range(self.buttons_layout.count())): 
            self.buttons_layout.itemAt(i).widget().setParent(None)

        for idx, row in rutas.iterrows():
            tecnico_button = QPushButton(f"Mostrar estadísticas de {row['Res_Label']}")
            tecnico_button.clicked.connect(lambda _, r=row: self.mostrar_estadisticas_tecnico(r))
            self.buttons_layout.addWidget(tecnico_button)

    def mostrar_estadisticas_tecnico(self, ruta):
        """
    Muestra estadísticas detalladas de una ruta específica en el área de resultados.
    Args:
        ruta (pd.Series): Fila del DataFrame con los datos de la ruta seleccionada.
    """
        estadisticas = (
            f"<div style='border-radius: 10px; background-color: #f8f9fa; padding: 15px; margin: 10px 0; "
            f"border: 1px solid #ccc; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); font-size: 14px;'>"
            f"<h3 style='color: #046d94; margin-bottom: 5px;'>👨‍🔧 Técnico: {ruta['Res_Label']}</h3>"
            f"<p><b>&nbsp;&nbsp;&nbsp;&nbsp;🏷️ Orden:</b> {ruta['Evt_Label']}</p>"
            f"<p><b>&nbsp;&nbsp;&nbsp;&nbsp;⏳ Duración:</b> {ruta['Dat_Hours']:.2f} horas</p>"
            f"<p><b>&nbsp;&nbsp;&nbsp;&nbsp;📏 Distancia:</b> {ruta['Distancia_lat_long']:.2f} km</p>"
            f"<p><b>&nbsp;&nbsp;&nbsp;&nbsp;📅 Fecha:</b> {ruta['FechaHoraInicio'].strftime('%d-%m-%Y')}</p>"
            f"<p><b>&nbsp;&nbsp;&nbsp;&nbsp;🕒 Hora de inicio:</b> {ruta['FechaHoraInicio'].strftime('%H:%M:%S')}</p>"
            f"</div>"
        )
        # Crear una etiqueta con las estadísticas
        label = QLabel(estadisticas)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)  
        label.setWordWrap(True)  
        label.setStyleSheet("font-size: 15px;")  
        self.result_layout.addWidget(label)  
