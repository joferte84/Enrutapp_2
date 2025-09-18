from PyQt5.QtWidgets import (
    QLabel, QVBoxLayout, QTextEdit, QWidget,
    QSplitter, QListWidget, QListWidgetItem,
    QDateEdit, QLineEdit, QPushButton,
    QHBoxLayout, QDialog, QScrollArea
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView

import folium
from folium import CustomIcon, Popup
import os
import re
import pandas as pd
import math
import base64
import sys

from modulos.utils import cargar_configuracion
from modulos.logger_config import logger
from modulos.api_manager import APIManager


def get_adjusted_coords(coords, adjustment_factor=0.01, index=0):
    """Genera coordenadas ligeramente ajustadas para evitar superposición exacta."""

    angle = index * 30  # Aumentar el ángulo para un despliegue más amplio
    new_lat = coords[0] + adjustment_factor * math.cos(math.radians(angle))
    new_lon = coords[1] + adjustment_factor * math.sin(math.radians(angle))
    return (new_lat, new_lon)

def format_order_popup(row):
    """Genera el contenido HTML del popup para cada orden."""
    fecha_formateada = row['Fecha'].strftime('%d/%m/%Y') if pd.notna(row['Fecha']) else "Fecha desconocida"
    codigo_postal = row['CP'] if pd.notna(row['CP']) else "Código postal no disponible"
    inicio = row['Dat_StartHour'] if pd.notna(row['Dat_StartHour']) else "Hora desconocida"
    fin = row['Dat_EndHour'] if pd.notna(row['Dat_EndHour']) else "Hora desconocida"
    tecnico = row['Nombre Tecnico'] if pd.notna(row['Nombre Tecnico']) else "Técnico no asignado"

    return f"""
    <div style="font-size: 14px; width: 400px; line-height: 1.2; padding: 5px;">
        <p><b>Técnico:</b> {tecnico}</p>
        <p><b>Orden:</b> {row['Evt_Label']}</p>
        <p><b>Fecha:</b> {fecha_formateada}</p>
        <p><b>Código Postal:</b> {codigo_postal}</p>
        <p><b>Horario:</b> {inicio} - {fin}</p>
    </div>
    """
def get_map_path():
    """Devuelve la ruta del archivo map.html dentro de modulos/data."""
    return os.path.join(get_data_dir(), "map.html")



def get_data_dir():
    """Devuelve la ruta del directorio de datos en desarrollo o en entorno empaquetado con PyInstaller."""
    base_dir = os.path.join(os.getcwd(), "modulos")  # Desarrollo
    if getattr(sys, "frozen", False):
        base_dir = os.path.join(sys._MEIPASS, "modulos")  # PyInstaller

    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)  # Crea la carpeta si no existe

    return data_dir



class BuscarTecnicoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.data = None
        self.api_manager = APIManager()

        self.status_label = QLabel(" ", self)
        self.status_label.setStyleSheet("font-size: 16px; color: black")
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Mostrar Rutas")
        self.resize(1000, 600)

        layout = QVBoxLayout()
        splitter = QSplitter(Qt.Horizontal)  # Splitter horizontal

        # Panel izquierdo para selección y resultados
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignTop)

        # ListWidget para seleccionar múltiples técnicos
        tecnico_label = QLabel("Selecciona técnicos:")
        tecnico_label.setStyleSheet("font-size: 16px; color: black;")
        self.tecnico_list = QListWidget()
        self.tecnico_list.setSelectionMode(QListWidget.MultiSelection)
        self.tecnico_list.itemSelectionChanged.connect(self.filtrar_por_tecnicos)

        left_layout.addWidget(tecnico_label)
        left_layout.addWidget(self.tecnico_list)

        # Selector de rango de fechas
        start_label = QLabel("Fecha de inicio:")
        start_label.setStyleSheet("font-size: 16px; color: black;")
        self.start_date_edit = QDateEdit(self)
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDisplayFormat("dd/MM/yyyy")
        tomorrow = pd.Timestamp.now().to_pydatetime() + pd.Timedelta(days=1)
        self.start_date_edit.setDate(tomorrow)
        self.start_date_edit.setFocusPolicy(Qt.NoFocus)
        self.start_date_edit.setStyleSheet("""
            QDateEdit {
                border: 2px solid #046d94;  /* Borde azul */
                border-radius: 5px;
                padding: 5px;
                background-color: #ffffff;
                font-size: 14px;
            }
            QDateEdit::drop-down {
                width: 30px;  /* Hace más ancho el botón */
                background-color: #046d94;  /* Fondo azul */
                border-left: 2px solid #388E3C;
            }
            QDateEdit::down-arrow {
                color: white;
                font-size: 16px;
            }
            QCalendarWidget QToolButton { 
                color: white;  /* Cambia el color del mes y año */
                font-size: 16px;
            }
        """)

        end_label = QLabel("Fecha de fin:")
        end_label.setStyleSheet("font-size: 16px; color: black;")
        self.end_date_edit = QDateEdit(self)
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDisplayFormat("dd/MM/yyyy")
        self.end_date_edit.setDate(tomorrow)
        self.end_date_edit.setFocusPolicy(Qt.NoFocus)
        self.end_date_edit.setStyleSheet("""
            QDateEdit {
                border: 2px solid #046d94;  /* Borde azul */
                border-radius: 5px;
                padding: 5px;
                background-color: #ffffff;
                font-size: 14px;
            }
            QDateEdit::drop-down {
                width: 30px;  /* Botón más ancho */
                background-color: #046d94;  /* Fondo azul */
                border-left: 2px solid #1976D2;
            }
            QDateEdit::down-arrow {
                color: white;
                font-size: 16px;
            }
            QCalendarWidget QToolButton { 
                color: black;  /* Cambia el color del mes y año */
                font-size: 16px;
            }
        """)


        left_layout.addWidget(start_label)
        left_layout.addWidget(self.start_date_edit)
        left_layout.addWidget(end_label)
        left_layout.addWidget(self.end_date_edit)

        # Conectar cambios en fechas
        self.start_date_edit.dateChanged.connect(self.filtrar_por_fecha)
        self.end_date_edit.dateChanged.connect(self.filtrar_por_fecha)

        # Área de texto para mostrar resultados
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setStyleSheet("font-size: 14px;")

        # Botón para abrir la ventana emergente con órdenes
        self.ver_ordenes_button = QPushButton("Ver Órdenes en Ventana")
        self.ver_ordenes_button.setFixedHeight(50)
        self.ver_ordenes_button.setStyleSheet("""
            QPushButton {
                background-color: #04a4d3;
                color: white;
                font-size: 16px;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #049cc4;
            }
            QPushButton:pressed {
                background-color: #046d94;
            }
            """)
        self.ver_ordenes_button.clicked.connect(self.mostrar_ordenes_filtradas)


        bottom_layout = QVBoxLayout()
        bottom_layout.addWidget(self.results_text)
        bottom_layout.addWidget(self.ver_ordenes_button)

        left_layout.addLayout(bottom_layout)

        # Panel derecho para el mapa
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        #  Crear layout horizontal para la entrada y el botón
        cp_layout = QHBoxLayout()

        # Campo de entrada de código postal
        self.cp_input = QLineEdit()
        self.cp_input.setFixedHeight(36)
        self.cp_input.setPlaceholderText("Introduce un código postal")
        self.cp_input.setStyleSheet("font-size: 14px; border-radius: 5px; padding: 5px; border: 2px solid #046d94;")

                
        # Botón para agregar marcador
        self.add_marker_button = QPushButton("Agregar Marcador")
        self.add_marker_button.setFixedHeight(36)
        self.add_marker_button.setStyleSheet("""
            QPushButton {
                background-color: #04a4d3;
                color: white;
                font-size: 16px;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #049cc4;
            }
            QPushButton:pressed {
                background-color: #046d94;
            }
            """)
        # Nuevo campo de entrada de código postal para calcular distancia
        self.cp_distance_input = QLineEdit()
        self.cp_distance_input.setFixedHeight(36)
        self.cp_distance_input.setPlaceholderText("Código postal destino")
        self.cp_distance_input.setStyleSheet("font-size: 14px; border-radius: 5px; padding: 5px; border: 2px solid #046d94;")

        # Botón para calcular distancia
        self.calculate_distance_button = QPushButton("Calcular Distancia")
        self.calculate_distance_button.setFixedHeight(36)
        self.calculate_distance_button.setStyleSheet("""
            QPushButton {
                background-color: #04a4d3;
                color: white;
                font-size: 16px;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #049cc4;
            }
            QPushButton:pressed {
                background-color: #046d94;
            }
        """)

        # Agregar los widgets al layout horizontal
        cp_layout.addWidget(self.cp_input)
        cp_layout.addWidget(self.add_marker_button)
        cp_layout.addWidget(self.cp_distance_input)
        cp_layout.addWidget(self.calculate_distance_button)


        #  Añadir el `QHBoxLayout()` al `right_layout`
        right_layout.addLayout(cp_layout)

        # **Área de texto para mostrar distancia y duración con QTextEdit**
        self.distance_text = QTextEdit()
        self.distance_text.setReadOnly(True)  
        self.distance_text.setFixedHeight(42)
        self.distance_text.setStyleSheet("font-size: 16px; border-radius: 5px; border: 2px solid #046d94;")

        # Añadir el QTextEdit debajo del layout
        right_layout.addWidget(self.distance_text)

        # Visor de mapas
        self.map_view = QWebEngineView()
        self.load_map()
        right_layout.addWidget(self.map_view)

        # Agregar los paneles al splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 800])  

        layout.addWidget(splitter)
        self.setLayout(layout)

        self.cargar_datos()

        self.add_marker_button.clicked.connect(self.agregar_marcador_codigo_postal)

        self.calculate_distance_button.clicked.connect(self.calcular_distancia)


    def load_map(self):
        """Carga el mapa inicial."""
        os.makedirs(get_data_dir(), exist_ok=True)  # Asegurar que el directorio exista
        map_path = get_map_path()
        m = folium.Map(location=[40.4168, -3.7038], zoom_start=6)
        m.save(map_path)
        self.map_view.setUrl(QUrl.fromLocalFile(os.path.abspath(map_path)))

    def cargar_datos(self):
        """Carga los datos y solo muestra en la lista de técnicos aquellos que tienen órdenes, en orden alfabético.
        Al iniciar, filtra automáticamente por la fecha de mañana."""
        configuracion = cargar_configuracion()
        archivo_excel_ordenes = configuracion.get('archivo_excel')
        archivo_cp_tecnicos_adt = configuracion.get('archivo_cp_tecnicos_adt')
        archivo_codigos_postales = configuracion.get('archivo_codigos_postales')

        try:
            df_ordenes = pd.read_excel(archivo_excel_ordenes)
            self.df_tecnicos = pd.read_excel(archivo_cp_tecnicos_adt, sheet_name="Hoja1")
            self.df_codigos_postales = pd.read_excel(archivo_codigos_postales)

            self.df_codigos_postales['codigo_postal'] = self.df_codigos_postales['codigo_postal'].astype(str).str.zfill(5)
            self.df_tecnicos['Codigo Postal'] = self.df_tecnicos['Codigo Postal'].astype(str).str.zfill(5)

            # Merge de latitudes/longitudes
            self.df_tecnicos = pd.merge(
                self.df_tecnicos,
                self.df_codigos_postales[['codigo_postal', 'Latitud', 'Longitud']],
                left_on='Codigo Postal',
                right_on='codigo_postal',
                how='left'
            )

            if 'Evt_PROVINCIA' in df_ordenes.columns:
                df_ordenes['CP'] = df_ordenes['Evt_PROVINCIA'].str.split('-').str[0]
            else:
                raise ValueError("La columna 'Evt_PROVINCIA' no está presente en el archivo de órdenes.")

            # Procesar fechas
            if {'Dat_Year', 'Dat_Month', 'Dat_Day'}.issubset(df_ordenes.columns):
                df_ordenes['Fecha'] = pd.to_datetime(
                    df_ordenes[['Dat_Year', 'Dat_Month', 'Dat_Day']].rename(
                        columns={'Dat_Year': 'year', 'Dat_Month': 'month', 'Dat_Day': 'day'}
                    )
                )
            else:
                raise ValueError("Faltan columnas de fecha en el DataFrame de órdenes.")

            # Merge de órdenes y técnicos
            self.df_tecnicos.rename(columns={'Nombre Enrutador': 'Res_Label'}, inplace=True)
            df_ordenes['Res_Label'] = df_ordenes['Res_Label'].apply(self.limpiar_y_capitalizar_nombre)
            self.df_tecnicos['Res_Label'] = self.df_tecnicos['Res_Label'].apply(self.limpiar_y_capitalizar_nombre)

            df_merged = pd.merge(
                df_ordenes,
                self.df_tecnicos[['Res_Label', 'Nombre Tecnico']],
                on='Res_Label',
                how='left'
            )

            # Merge con coordenadas
            df_final = pd.merge(
                df_merged,
                self.df_codigos_postales[['codigo_postal', 'Latitud', 'Longitud']],
                left_on='CP',
                right_on='codigo_postal',
                how='left'
            )

            # Filtrar técnicos que tienen órdenes
            tecnicos_con_ordenes = df_final['Nombre Tecnico'].dropna().unique()

            # Ordenar la lista de técnicos alfabéticamente
            tecnicos_con_ordenes = sorted(tecnicos_con_ordenes)

            # Asignar datos finales
            self.data = df_final.dropna(subset=['Nombre Tecnico'])

            # Limpiar y cargar solo técnicos con órdenes en la lista
            self.tecnico_list.clear()
            self.tecnico_colors = {}  # Reiniciar colores de técnicos

            for i, tecnico in enumerate(tecnicos_con_ordenes):
                self.tecnico_colors[tecnico] = QColor.fromHsv(i * 360 // len(tecnicos_con_ordenes), 200, 255)
                item = QListWidgetItem(tecnico)
                item.setBackground(self.tecnico_colors[tecnico])
                self.tecnico_list.addItem(item)

            # Filtrar automáticamente por la fecha seleccionada (mañana)
            self.filtrar_por_fecha()

        except Exception as e:
            # Verificar si `status_label` está inicializado antes de usarlo
            if hasattr(self, 'status_label'):
                self.status_label.setText(f"Error al cargar los datos: {e}")
            else:
                print(f"Error al cargar los datos: {e}")

    def limpiar_y_capitalizar_nombre(self, texto):
        if pd.notna(texto):
            # Eliminar caracteres no deseados y espacios extra
            limpio = re.sub(r'_x000D_|[\n\r]+', '', texto)
            return re.sub(r'\s+', ' ', limpio).strip()
        return ""

    def show_results(self, ordenes):
        """Muestra las órdenes en la lista con los nuevos formatos."""
        # Filtrar las órdenes para incluir solo aquellas con Evt_Type == "Tarea"
        ordenes = ordenes[ordenes['Evt_Type'] == "Tarea"]

        # Limpiar el área de resultados antes de imprimir nuevas órdenes
        self.results_text.clear()

        for _, row in ordenes.iterrows():
            # Formatear la fecha o manejar fechas faltantes
            fecha_formateada = row['Fecha'].strftime('%d/%m/%Y') if pd.notna(row['Fecha']) else "Fecha desconocida"
            tecnico = row['Nombre Tecnico'] if pd.notna(row['Nombre Tecnico']) else "Sin técnico"
            inicio = row['Dat_StartHour'] if pd.notna(row['Dat_StartHour']) else "Sin hora"
            final = row['Dat_EndHour'] if pd.notna(row['Dat_EndHour']) else "Sin hora"
            codigo_postal = row['CP'] if pd.notna(row['CP']) else "CP desconocido"
            orden = row['Evt_Label']

            # Agregar cada orden al área de texto con el formato especificado
            self.results_text.append(f"""
                <div style='border-radius: 12px; background-color: #f0f8ff; padding: 14px; margin: 10px 0; 
                    border: 1px solid #9ac7e2; box-shadow: 3px 3px 10px rgba(0,0,0,0.1); font-size: 14px;'>
                    <h3 style='color: #034e8f; margin-bottom: 6px;'>📋 Orden: {orden}</h3>
                    <p style='font-size: 13px;'><b>&nbsp;&nbsp;&nbsp;&nbsp;👨‍🔧 Técnico:</b> {tecnico}</p>
                    <p style='font-size: 13px;'><b>&nbsp;&nbsp;&nbsp;&nbsp;📍 CP:</b> {codigo_postal}</p>
                    <p style='font-size: 13px;'><b>&nbsp;&nbsp;&nbsp;&nbsp;📅 Fecha:</b> {fecha_formateada}</p>
                    <p style='font-size: 13px;'><b>&nbsp;&nbsp;&nbsp;&nbsp;🕒 Horario:</b> {inicio} - {final}</p>
                </div>
            """)

    def filtrar_por_fecha(self):
        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()
        selected_items = self.tecnico_list.selectedItems()
        tecnicos_seleccionados = [item.text() for item in selected_items]

        # Filtrar datos por técnicos y fechas
        filtered_data = self.data[
            (self.data['Fecha'].dt.date >= start_date) &
            (self.data['Fecha'].dt.date <= end_date)
        ]
        if tecnicos_seleccionados:
            filtered_data = filtered_data[filtered_data['Nombre Tecnico'].isin(tecnicos_seleccionados)]

        # Actualizar resultados
        self.show_results(filtered_data)
        self.update_map(filtered_data, tecnicos_seleccionados)

    def mostrar_ordenes_tecnico(self):
        tecnico_seleccionado = self.tecnico_dropdown.currentText()
        filtered_data = self.data[self.data['Nombre Tecnico'] == tecnico_seleccionado]
        ordenes_filtradas = self.filtrar_ordenes_por_formato(filtered_data)

        self.show_results(ordenes_filtradas)
        self.update_map(ordenes_filtradas, tecnico_seleccionado)

    def show_message(self, message):
        self.results_text.setHtml(f"<b>{message}</b>")

    def filtrar_por_tecnicos(self):
        """Filtra por técnicos seleccionados:
        - Si hay técnicos seleccionados, muestra solo sus órdenes del día de mañana.
        - Si no hay técnicos seleccionados, muestra todas las órdenes del día de mañana.
        """
        selected_items = self.tecnico_list.selectedItems()
        tecnicos_seleccionados = [item.text() for item in selected_items]

        # Fijar automáticamente la fecha en mañana
        tomorrow = pd.Timestamp.now().to_pydatetime() + pd.Timedelta(days=1)
        self.start_date_edit.setDate(tomorrow)
        self.end_date_edit.setDate(tomorrow)

        # Si hay técnicos seleccionados, filtrar solo por ellos
        if tecnicos_seleccionados:
            self.filtrar_ordenes(tecnicos=tecnicos_seleccionados, fechas=[tomorrow.date()])
        else:
            # Si NO hay técnicos seleccionados, mostrar TODAS las órdenes del día de mañana
            self.filtrar_ordenes(fechas=[tomorrow.date()])

    def filtrar_por_fecha(self):
        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()
        selected_items = self.tecnico_list.selectedItems()
        tecnicos_seleccionados = [item.text() for item in selected_items]

        # Filtrar datos por técnicos y fechas
        filtered_data = self.data[
            (self.data['Fecha'].dt.date >= start_date) & 
            (self.data['Fecha'].dt.date <= end_date)
        ]
        if tecnicos_seleccionados:
            filtered_data = filtered_data[filtered_data['Nombre Tecnico'].isin(tecnicos_seleccionados)]

        # Actualizar resultados
        self.show_results(filtered_data)
        self.update_map(filtered_data, tecnicos_seleccionados)


    def filtrar_ordenes(self, tecnicos=None, fechas=None):
        # Filtra las órdenes por técnicos y fechas
        filtered_data = self.data
        if tecnicos:
            filtered_data = filtered_data[filtered_data['Nombre Tecnico'].isin(tecnicos)]
        if fechas:
            filtered_data = filtered_data[filtered_data['Fecha'].dt.date.isin(fechas)]

        self.show_results(filtered_data)
        self.update_map(filtered_data, tecnicos)


    def filtrar_ordenes_por_formato(self, ordenes):
        """Filtra las órdenes que cumplen con el formato específico de 'letra+letra+nnnnnnn' y son del tipo 'Tarea'."""
        pattern = re.compile(r'^[A-Za-z]{2}\d{6,7}(-\d{2})?$')
        # Asegúrate de que 'Evt_Label' es una cadena antes de aplicar la expresión regular.
        ordenes.loc[:, 'Evt_Label'] = ordenes['Evt_Label'].astype(str)

        return ordenes[(
            ordenes['Evt_Type'] == 'Tarea') & 
            (ordenes['Evt_Label'].apply(lambda x: bool(pattern.match(x))))
        ]
    
    def update_map(self, ordenes_filtradas, tecnicos_seleccionados=None, extra_marker=None):
        """Actualiza el mapa asegurando que:
        - Se impriman todas las órdenes del día seleccionado por defecto.
        - Si hay técnicos seleccionados, se impriman sus rutas desde su casa.
        - Se pueda agregar un marcador adicional sin afectar la visualización existente.
        """

        map_path = get_map_path()
        
        # Definir la ubicación central predeterminada
        if tecnicos_seleccionados:
            coords = self.df_tecnicos[self.df_tecnicos['Nombre Tecnico'].isin(tecnicos_seleccionados)][['Latitud', 'Longitud']].mean()
            center_location = [coords['Latitud'], coords['Longitud']]
        else:
            if not ordenes_filtradas.empty:
                coords = ordenes_filtradas[['Latitud', 'Longitud']].mean()
                center_location = [coords['Latitud'], coords['Longitud']]
            else:
                center_location = [40.4168, -3.7038]  # Madrid por defecto si no hay datos

        # Si se agrega un marcador extra, lo usamos como nueva ubicación central
        if extra_marker:
            lat, lon, popup_text, color = extra_marker
            center_location = [lat, lon]  # Cambiamos el centro del mapa

        # Crear el mapa centrado en la última ubicación agregada
        self.mapa_folium = folium.Map(location=center_location, zoom_start=7)

        # Si no hay técnicos seleccionados, mostrar solo órdenes sin rutas ni casas
        if not tecnicos_seleccionados:
            if not ordenes_filtradas.empty:
                ordenes_validas = ordenes_filtradas.dropna(subset=['Latitud', 'Longitud']).copy()
                if not ordenes_validas.empty:
                    for _, row in ordenes_validas.iterrows():
                        coords = [row['Latitud'], row['Longitud']]
                        tecnico = row['Nombre Tecnico']
                        color_qt = self.tecnico_colors.get(tecnico, QColor("blue"))
                        color_hex = color_qt.name()

                        popup_content = format_order_popup(row)

                        # SVG para el icono de cada orden
                        svg_content = f"""
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color_hex}" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="12" cy="12" r="10"/>
                        </svg>
                        """
                        svg_base64 = base64.b64encode(svg_content.encode()).decode()
                        icon_url = f"data:image/svg+xml;base64,{svg_base64}"

                        custom_icon = CustomIcon(
                            icon_image=icon_url,
                            icon_size=(20, 20)
                        )

                        folium.Marker(
                            coords,
                            popup=popup_content,
                            icon=custom_icon
                        ).add_to(self.mapa_folium)

        # Si hay técnicos seleccionados, agregar casas y rutas
        if tecnicos_seleccionados:
            rutas_por_tecnico_fecha = {}

            for tecnico in tecnicos_seleccionados:
                tecnico_info = self.df_tecnicos[self.df_tecnicos['Nombre Tecnico'] == tecnico]
                if not tecnico_info.empty:
                    lat_casa, lon_casa = tecnico_info.iloc[0]['Latitud'], tecnico_info.iloc[0]['Longitud']

                    rutas_por_tecnico_fecha[tecnico] = {}

                    popup_html = f"""
                        <div style="width: 300px; font-size: 16px; text-align: center;">
                            Casa de {tecnico} - Código Postal: {tecnico_info.iloc[0]['Codigo Postal']}
                        </div>
                    """

                    # **SVG para la casa del técnico**
                    svg_house = f"""
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="black" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polygon points="5,12 12,5 19,12 19,19 5,19" />
                        <rect x="9" y="14" width="6" height="5" fill="white" stroke="black"/>
                    </svg>
                    """
                    svg_base64_house = base64.b64encode(svg_house.encode()).decode()
                    icon_url_house = f"data:image/svg+xml;base64,{svg_base64_house}"

                    custom_icon_house = CustomIcon(
                        icon_image=icon_url_house,
                        icon_size=(30, 30)
                    )

                    folium.Marker(
                        [lat_casa, lon_casa],
                        popup=Popup(popup_html, max_width=300),
                        icon=custom_icon_house
                    ).add_to(self.mapa_folium)

            if not ordenes_filtradas.empty:
                ordenes_validas = ordenes_filtradas.dropna(subset=['Latitud', 'Longitud']).copy()
                if not ordenes_validas.empty:
                    ordenes_validas = ordenes_validas.sort_values(by=['Fecha', 'Dat_StartHour'])

                    for (tecnico, fecha), grupo in ordenes_validas.groupby(['Nombre Tecnico', 'Fecha']):
                        if tecnico in rutas_por_tecnico_fecha:
                            if fecha not in rutas_por_tecnico_fecha[tecnico]:
                                rutas_por_tecnico_fecha[tecnico][fecha] = []

                            lat_casa, lon_casa = self.df_tecnicos.loc[
                                self.df_tecnicos['Nombre Tecnico'] == tecnico, ['Latitud', 'Longitud']
                            ].values[0]

                            rutas_por_tecnico_fecha[tecnico][fecha].append([lat_casa, lon_casa])

                            coordenadas_contador = {}

                            for _, row in grupo.iterrows():
                                coords = (row['Latitud'], row['Longitud'])

                                if coords in coordenadas_contador:
                                    coordenadas_contador[coords] += 1
                                else:
                                    coordenadas_contador[coords] = 0

                                adjusted_coords = get_adjusted_coords(coords, adjustment_factor=0.01, index=coordenadas_contador[coords])

                                rutas_por_tecnico_fecha[tecnico][fecha].append(adjusted_coords)

                                color_qt = self.tecnico_colors.get(tecnico, QColor("blue"))
                                color_hex = color_qt.name()

                                popup_content = format_order_popup(row)

                                svg_content = f"""
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color_hex}" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <circle cx="12" cy="12" r="10"/>
                                </svg>
                                """
                                svg_base64 = base64.b64encode(svg_content.encode()).decode()
                                icon_url = f"data:image/svg+xml;base64,{svg_base64}"

                                custom_icon = CustomIcon(
                                    icon_image=icon_url,
                                    icon_size=(20, 20)
                                )

                                folium.Marker(
                                    adjusted_coords,
                                    popup=popup_content,
                                    icon=custom_icon
                                ).add_to(self.mapa_folium)

            colores_ruta = ["red", "blue", "green", "purple", "orange", "brown", "black"]
            color_idx = 0

            for tecnico, fechas in rutas_por_tecnico_fecha.items():
                for fecha, ruta in fechas.items():
                    color_ruta = colores_ruta[color_idx % len(colores_ruta)]
                    color_idx += 1

                    if len(ruta) > 1:
                        folium.PolyLine(
                            ruta, color=color_ruta, weight=3, opacity=0.7, tooltip=f"Ruta {fecha.strftime('%d/%m/%Y')} - {tecnico}"
                        ).add_to(self.mapa_folium)

        if extra_marker:
            lat, lon, popup_text, color = extra_marker  # Ahora siempre tendrá 4 valores

            # Crear el icono en el color especificado
            svg_marker = f"""
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/>
                <text x="12" y="16" font-size="12" text-anchor="middle" fill="white">i</text>
            </svg>
            """
            svg_base64_marker = base64.b64encode(svg_marker.encode()).decode()
            icon_url_marker = f"data:image/svg+xml;base64,{svg_base64_marker}"

            custom_icon_marker = CustomIcon(
                icon_image=icon_url_marker,
                icon_size=(30, 30)
            )

            folium.Marker(
                [lat, lon],
                popup=Popup(popup_text, max_width=200),
                icon=custom_icon_marker
            ).add_to(self.mapa_folium)

        self.mapa_folium.save(map_path)
        self.map_view.setUrl(QUrl.fromLocalFile(os.path.abspath(map_path)))
        logger.info("El agente ha actualizado el mapa")

    def agregar_marcador_codigo_postal(self):
        """Añade un marcador al mapa basado en el código postal ingresado sin perder la ruta del técnico."""

        codigo_postal = self.cp_input.text().strip()

        if not codigo_postal:
            self.show_message("Introduce un código postal válido.")
            return

        # Buscar el código postal en la copia local
        resultado = self.df_codigos_postales[self.df_codigos_postales["codigo_postal"] == codigo_postal]

        if resultado.empty:
            self.show_message("Código postal no encontrado.")
            return

        lat, lon = resultado.iloc[0]["Latitud"], resultado.iloc[0]["Longitud"]

        # Obtener los filtros actuales de la interfaz
        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()

        # Obtener técnicos seleccionados en la interfaz
        selected_items = self.tecnico_list.selectedItems()
        tecnicos_seleccionados = [item.text() for item in selected_items]

        # Aplicar los filtros a `self.data`
        ordenes_filtradas = self.data[
            (self.data['Fecha'].dt.date >= start_date) &
            (self.data['Fecha'].dt.date <= end_date)
        ]

        if tecnicos_seleccionados:
            ordenes_filtradas = ordenes_filtradas[ordenes_filtradas['Nombre Tecnico'].isin(tecnicos_seleccionados)]

        logger.info(f"Se ha agregado un 'marcador' para el Código Postal: {codigo_postal} ({lat}, {lon}).")

        popup_html = f"""
            <div style="width: 100%; font-size: 16px; text-align: center; padding: 5px;">
                <strong>Código Postal:</strong> <span style="font-weight: bold;">{codigo_postal}</span>
            </div>
        """



        self.update_map(ordenes_filtradas, tecnicos_seleccionados, extra_marker=(lat, lon, popup_html, "white"))

    def calcular_distancia(self):
        """Obtiene la distancia y la duración del trayecto entre dos códigos postales usando la API seleccionada,
        y agrega un marcador en el mapa en el código postal de destino sin sobrescribir los datos existentes.
        """

        cp_origen = self.cp_input.text().strip()
        cp_destino = self.cp_distance_input.text().strip()

        if not cp_origen or not cp_destino:
            self.distance_text.setText("Introduce ambos códigos postales.")
            return

        # Buscar coordenadas en el dataframe local
        origen = self.df_codigos_postales[self.df_codigos_postales["codigo_postal"] == cp_origen]
        destino = self.df_codigos_postales[self.df_codigos_postales["codigo_postal"] == cp_destino]

        if origen.empty or destino.empty:
            self.distance_text.setText("No se encontraron coordenadas para uno o ambos códigos postales.")
            return

        lat_origen, lon_origen = origen.iloc[0]["Latitud"], origen.iloc[0]["Longitud"]
        lat_destino, lon_destino = destino.iloc[0]["Latitud"], destino.iloc[0]["Longitud"]

        # Seleccionar la API antes de la consulta para loggear el nombre
        api_seleccionada = self.api_manager.seleccionar_api()
        api_nombre = api_seleccionada["name"]

        # Llamar a la API para calcular la distancia
        distancia, duracion = self.api_manager.obtener_distancia(lat_origen, lon_origen, lat_destino, lon_destino)

        if distancia is not None and duracion is not None:
            self.distance_text.setText(f"📍 Distancia: {distancia:.2f} km ⏳ Duración: {duracion:.1f} min")
            
            logger.info(f"El usuario calculó una distancia con la API {api_nombre}")

            # Crear el marcador para el código postal destino sin sobrescribir el mapa
            popup_html = f"""
                <div style="width: 300px; font-size: 16px; text-align: center;">
                    Destino: <b>{cp_destino}</b>
                </div>
            """

            self.add_marker_to_map(lat_destino, lon_destino, popup_html, "gray")

        else:
            self.distance_text.setText("No se pudo calcular la distancia.")

    def add_marker_to_map(self, lat, lon, popup_text, color="gray"):
        """Añade un marcador al mapa sin sobrescribir los datos existentes."""
        
        # Crear el icono en el color especificado
        svg_marker = f"""
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <text x="12" y="16" font-size="12" text-anchor="middle" fill="white">i</text>
        </svg>
        """
        svg_base64_marker = base64.b64encode(svg_marker.encode()).decode()
        icon_url_marker = f"data:image/svg+xml;base64,{svg_base64_marker}"

        custom_icon_marker = CustomIcon(
            icon_image=icon_url_marker,
            icon_size=(30, 30)
        )

        folium.Marker(
            [lat, lon],
            popup=Popup(popup_text, max_width=200),
            icon=custom_icon_marker
        ).add_to(self.mapa_folium)

        # Guardar y actualizar el mapa en la ubicación correcta
        map_path = get_map_path()  # ⚡ Obtiene la ruta correcta en `modulos/data/`
        self.mapa_folium.save(map_path)
        self.map_view.setUrl(QUrl.fromLocalFile(os.path.abspath(map_path)))

    def filtrar_datos_actuales(self):
        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()
        selected_items = self.tecnico_list.selectedItems()
        tecnicos_seleccionados = [item.text() for item in selected_items]
        filtered_data = self.data[(self.data['Fecha'].dt.date >= start_date) & (self.data['Fecha'].dt.date <= end_date)]
        if tecnicos_seleccionados:
            filtered_data = filtered_data[filtered_data['Nombre Tecnico'].isin(tecnicos_seleccionados)]
        return filtered_data

    def mostrar_ordenes_filtradas(self):
        ordenes_df = self.filtrar_datos_actuales()
        self.mostrar_ordenes_dialog(ordenes_df)

    def mostrar_ordenes_dialog(self, ordenes_df):
        """
        Muestra un cuadro flotante con las órdenes y permite hacer clic en ellas para centrar el mapa.
        """
        self.dialog = QDialog(self)
        self.dialog.setWindowTitle("Órdenes")
        self.dialog.setGeometry(450, 250, 600, 800)
        self.dialog.setWindowModality(Qt.NonModal)
        self.dialog.setAttribute(Qt.WA_DeleteOnClose)

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        title_label = QLabel("📌 Órdenes Asignadas")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #046d94;")

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        tarea_df = ordenes_df[ordenes_df['Evt_Type'] == 'Tarea']

        if tarea_df.empty:
            mensaje_label = QLabel("No se encontraron órdenes de tipo 'Tarea'.")
            mensaje_label.setAlignment(Qt.AlignCenter)
            scroll_layout.addWidget(mensaje_label)
        else:
            for _, row in tarea_df.iterrows():
                fecha = row['Fecha'].strftime('%d/%m/%Y') if pd.notna(row['Fecha']) else "Fecha desconocida"
                orden_texto = (
                    f"<div style='cursor: pointer; border-radius: 12px; background-color: #f0f8ff; padding: 14px; margin: 10px 0; "
                    f"border: 1px solid #9ac7e2; box-shadow: 3px 3px 10px rgba(0,0,0,0.1); font-size: 14px;'>"
                    f"<h3 style='color: #034e8f;'>📋 Orden: {row['Evt_Label']}</h3>"
                    f"<p><b>&nbsp;&nbsp;&nbsp;&nbsp;👨‍🔧 Técnico:</b> {row.get('Nombre Tecnico', 'N/A')}</p>"
                    f"<p><b>&nbsp;&nbsp;&nbsp;&nbsp;📍 CP:</b> {row.get('CP', 'N/A')}</p>"
                    f"<p><b>&nbsp;&nbsp;&nbsp;&nbsp;📅 Fecha:</b> {row['Fecha'].strftime('%d/%m/%Y') if pd.notna(row['Fecha']) else 'Desconocida'}</p>"
                    f"<p><b>&nbsp;&nbsp;&nbsp;&nbsp;🕒 Horario:</b> {row.get('Dat_StartHour', 'N/A')} - {row.get('Dat_EndHour', 'N/A')}</p>"
                    f"</div>"
                )

                label = QLabel(orden_texto)
                label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                label.setWordWrap(True)
                label.setStyleSheet("font-size: 14px; cursor: pointer; background-color: white;")  # Fondo blanco
                
                # Guardamos las coordenadas en la propiedad `setProperty`
                label.setProperty("lat_lon", (row['Latitud'], row['Longitud']))
                label.mousePressEvent = lambda event, lbl=label: self.on_orden_clicked(lbl)

                scroll_layout.addWidget(label)

        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)

        close_button = QPushButton("Cerrar")
        close_button.setFixedHeight(40)
        close_button.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                font-weight: bold;
                padding: 15px;
                min-height: 30px;
                border-radius: 5px;
                background-color: #04a4d3;
                color: white;
            }
            QPushButton:hover {
                background-color: #049cc4;
            }
            QPushButton:pressed {
                background-color: #046d94;
            }
        """)
        close_button.clicked.connect(self.dialog.close)

        layout.addWidget(title_label)
        layout.addWidget(scroll_area)
        layout.addWidget(close_button)

        self.dialog.setLayout(layout)
        self.dialog.setStyleSheet("QDialog { background-color: #f0f0f0; border-radius: 12px; }")
        self.dialog.show()


    def on_orden_clicked(self, label):
        """
        Captura el clic en una orden y centra el mapa en su ubicación.
        """
        lat, lon = label.property("lat_lon")
        self.centrar_mapa_en_orden(lat, lon)


    def centrar_mapa_en_orden(self, lat, lon):
        """
        Centra el mapa en la orden seleccionada manteniendo filtros, colores SVG, casas y rutas.
        """
        selected_items = self.tecnico_list.selectedItems()
        tecnicos_seleccionados = [item.text() for item in selected_items]

        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()

        filtered_data = self.data[
            (self.data['Fecha'].dt.date >= start_date) &
            (self.data['Fecha'].dt.date <= end_date)
        ]
        if tecnicos_seleccionados:
            filtered_data = filtered_data[filtered_data['Nombre Tecnico'].isin(tecnicos_seleccionados)]

        m = folium.Map(location=[lat, lon], zoom_start=12)
        coordenadas_contador = {}

        # Agregar casas de técnicos seleccionados (negro)
        for tecnico in tecnicos_seleccionados:
            tecnico_info = self.df_tecnicos[self.df_tecnicos['Nombre Tecnico'] == tecnico]
            if not tecnico_info.empty:
                lat_casa, lon_casa = tecnico_info.iloc[0]['Latitud'], tecnico_info.iloc[0]['Longitud']
                popup_html = f"<div style='text-align: center; font-size: 16px;'><strong>Casa de {tecnico}</strong></div>"
                svg_house = f"""
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="black" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polygon points="5,12 12,5 19,12 19,19 5,19" />
                        <rect x="9" y="14" width="6" height="5" fill="white" stroke="black"/>
                    </svg>
                """
                icon_url_house = f"data:image/svg+xml;base64,{base64.b64encode(svg_house.encode()).decode()}"
                custom_icon_house = CustomIcon(icon_image=icon_url_house, icon_size=(30, 30))
                folium.Marker([lat_casa, lon_casa], popup=popup_html, icon=custom_icon_house).add_to(m)

        rutas_por_tecnico_fecha = {}
        for tecnico in tecnicos_seleccionados:
            rutas_por_tecnico_fecha[tecnico] = {}
            tecnico_data = filtered_data[filtered_data['Nombre Tecnico'] == tecnico].sort_values(by=['Fecha', 'Dat_StartHour'])
            for fecha, grupo in tecnico_data.groupby('Fecha'):
                rutas_por_tecnico_fecha[tecnico][fecha] = []
                lat_casa, lon_casa = self.df_tecnicos.loc[self.df_tecnicos['Nombre Tecnico'] == tecnico, ['Latitud', 'Longitud']].values[0]
                rutas_por_tecnico_fecha[tecnico][fecha].append([lat_casa, lon_casa])

                for _, row in grupo.iterrows():
                    if pd.isna(row['Latitud']) or pd.isna(row['Longitud']):
                        continue
                    coords = (row['Latitud'], row['Longitud'])
                    coordenadas_contador[coords] = coordenadas_contador.get(coords, 0) + 1
                    adjusted_coords = get_adjusted_coords(coords, adjustment_factor=0.001, index=coordenadas_contador[coords])

                    popup_content = format_order_popup(row)
                    color_qt = self.tecnico_colors.get(tecnico, QColor("blue"))
                    color_hex = color_qt.name()

                    # Usar SVG con el color asignado o verde si es la orden seleccionada
                    svg_marker = f"""
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{'green' if (row['Latitud'], row['Longitud']) == (lat, lon) else color_hex}" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="12" cy="12" r="10"/>
                        </svg>
                    """
                    icon_url = f"data:image/svg+xml;base64,{base64.b64encode(svg_marker.encode()).decode()}"
                    custom_icon = CustomIcon(icon_image=icon_url, icon_size=(20, 20))

                    folium.Marker(adjusted_coords, popup=popup_content, icon=custom_icon).add_to(m)
                    rutas_por_tecnico_fecha[tecnico][fecha].append(adjusted_coords)

        colores_ruta = ["red", "blue", "green", "purple", "orange", "brown", "black"]
        color_idx = 0
        for tecnico, fechas in rutas_por_tecnico_fecha.items():
            for fecha, ruta in fechas.items():
                color_ruta = colores_ruta[color_idx % len(colores_ruta)]
                color_idx += 1
                if len(ruta) > 1:
                    folium.PolyLine(ruta, color=color_ruta, weight=3, opacity=0.7, tooltip=f"Ruta {fecha.strftime('%d/%m/%Y')} - {tecnico}").add_to(m)

        map_path = get_map_path()
        m.save(map_path)
        self.map_view.setUrl(QUrl.fromLocalFile(os.path.abspath(map_path)))


        