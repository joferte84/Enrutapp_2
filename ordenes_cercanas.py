from PyQt5.QtCore import QCoreApplication, Qt
QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

from PyQt5.QtWidgets import (QVBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QScrollArea, QWidget, QHBoxLayout)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl

import pandas as pd
import folium
import warnings
import os

from modulos.utils import (cargar_listado_codigos_postales, obtener_lat_lon_de_direccion,
                           calcular_distancia_haversine, obtener_archivo_unico)
from modulos.logger_config import logger, get_data_dir
from modulos.tecnicos import get_adjusted_coords


warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

class OrdenesCercanas(QWidget):

    def __init__(self):
        """
    Inicializa la clase `OrdenesCercanas`, carga los datos necesarios y configura la interfaz gráfica.
    """
        super().__init__()
        
        try:
            self.excel_path = obtener_archivo_unico()
        except FileNotFoundError as e:
            logger.error(f"Error al buscar el archivo: {e}")
            self.excel_path = None

        self.listado_codigos_postales = self.load_codigos_postales() if self.excel_path else pd.DataFrame()
        self.data = self.load_data() if self.excel_path else pd.DataFrame()
        self.map_file = os.path.join(get_data_dir(), "map.html")

        self.init_ui()

    def init_ui(self):
        """
    Configura la interfaz gráfica de usuario, incluyendo el campo de entrada, botón de búsqueda,
    y el área de resultados con barra de desplazamiento.
    """
        self.setWindowTitle("Órdenes Cercanas con Mapa")
        self.resize(1000, 600)  

        BUTTON_STYLE = """
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
        """

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        input_layout = QHBoxLayout()
        self.cp_input = QLineEdit(self)
        self.cp_input.setPlaceholderText("Introduce un código postal (ej. 28001)")
        self.cp_input.setFixedSize(400, 40)
        self.cp_input.setStyleSheet("font-size: 16px; border-radius: 5px; padding: 5px; border: 2px solid #046d94;")

        search_button = QPushButton("Buscar", self)
        search_button.setFixedSize(250, 40)
        search_button.setStyleSheet(BUTTON_STYLE)
        search_button.clicked.connect(self.on_buscar_click)

        input_layout.addStretch()
        input_layout.addWidget(self.cp_input)
        input_layout.addWidget(search_button)
        input_layout.setAlignment(Qt.AlignRight)

        horizontal_layout = QHBoxLayout()
        horizontal_layout.setSpacing(10)

        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setStyleSheet("background-color: white; border: none;")
        self.scroll_area.setWidgetResizable(True)

        self.result_container = QWidget()
        self.result_layout = QVBoxLayout(self.result_container)
        self.scroll_area.setWidget(self.result_container)

        results_layout.addWidget(self.scroll_area)

        self.map_view = QWebEngineView()
        self.map_view.setFixedWidth(700)  
        self.map_view.setMinimumHeight(400)
        self.load_empty_map()

        horizontal_layout.addWidget(results_widget, stretch=2)  
        horizontal_layout.addWidget(self.map_view, stretch=3)

        main_layout.addLayout(input_layout)    
        main_layout.addLayout(horizontal_layout) 

    def load_codigos_postales(self):
        """
    Carga y valida el archivo `Listado-de-CP.xlsx`, asegurándose de que contenga las columnas necesarias
    y formatea los códigos postales para que tengan cinco dígitos.

    Returns:
        pd.DataFrame: DataFrame con códigos postales, latitudes y longitudes.
    Raises:
        ValueError: Si faltan columnas requeridas en el archivo.
    """
        archivo_codigos_postales = cargar_listado_codigos_postales()
        df = pd.read_excel(archivo_codigos_postales)
        df["codigo_postal"] = df["codigo_postal"].astype(str).str.zfill(5)
        return df

    def load_data(self):
        """
    Carga las primeras cinco hojas del archivo Excel, valida las columnas necesarias y combina los datos
    en un solo DataFrame. Realiza un merge con los códigos postales para agregar coordenadas y
    registra advertencias si hay códigos postales sin coordenadas.

    Returns:
        pd.DataFrame: DataFrame combinado con las columnas requeridas y coordenadas.
    """
        sheet_names = ["NORTE", "SUR", "ESTE", "LEVANTE", "CENTRO"]
        data_frames = []
        for sheet in sheet_names:
            try:
                df = pd.read_excel(self.excel_path, sheet_name=sheet)
                data_frames.append(df)
            except Exception as e:
                logger.error(f"Error al leer la hoja {sheet}: {e}")
        combined_data = pd.concat(data_frames, ignore_index=True)
        combined_data["CP"] = combined_data["CP"].astype(str).str.strip().str.zfill(5)
        self.listado_codigos_postales["codigo_postal"] = self.listado_codigos_postales["codigo_postal"].astype(str).str.zfill(5)
        combined_data = combined_data.merge(self.listado_codigos_postales, 
                                            left_on="CP", right_on="codigo_postal", how="left")
        return combined_data

    def load_empty_map(self):
        m = folium.Map(location=[40.4168, -3.7038], zoom_start=6)
        m.save(self.map_file)
        self.map_view.setUrl(QUrl.fromLocalFile(os.path.abspath(self.map_file)))

    def on_buscar_click(self):
        """
        Maneja el evento del botón de búsqueda. Obtiene el código postal introducido por el usuario,
        calcula las distancias a las órdenes cercanas usando Haversine, y muestra las 50 órdenes más cercanas.
        """
        cp_usuario = self.cp_input.text().strip()

        logger.info(f"Búsqueda realizada en 'Órdenes Cercanas': {cp_usuario}")
        
        if not cp_usuario:
            self.show_message("Introduce un código postal válido.")
            return

        lat_usuario, lon_usuario = obtener_lat_lon_de_direccion(cp_usuario, self.listado_codigos_postales)
        if lat_usuario is None or lon_usuario is None:
            self.show_message("Código postal no encontrado.")
            return

        # Guardamos las coordenadas del usuario para mantener el marcador rojo
        self.usuario_lat, self.usuario_lon = lat_usuario, lon_usuario

        data_valid = self.data.dropna(subset=["Latitud", "Longitud"]).copy()
        if data_valid.empty:
            self.show_message("No hay datos válidos con coordenadas para calcular distancias.")
            return

        data_valid["Distancia"] = data_valid.apply(
            lambda x: calcular_distancia_haversine(lat_usuario, lon_usuario, x["Latitud"], x["Longitud"]), axis=1)
        ordenes_cercanas = data_valid.sort_values(by="Distancia").head(25)

        self.show_results(ordenes_cercanas)
        self.update_map(ordenes_cercanas, lat_usuario, lon_usuario)

    def show_message(self, message):
        self.result_layout.addWidget(QLabel(message))

    def show_results(self, ordenes):
        """
    Muestra los resultados de las órdenes cercanas en el área de resultados con formato y estilo adecuados.
    Args:
        ordenes (pd.DataFrame): DataFrame que contiene las órdenes más cercanas a mostrar.
    """
        self.ordenes_mostradas = ordenes.copy()

        while self.result_layout.count():
            item = self.result_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for _, row in ordenes.iterrows():
            texto_opcion = (
                f"<div style='border-radius: 10px; background-color: #f8f9fa; padding: 15px; margin: 10px 0; "
                f"border: 1px solid #ccc; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); font-size: 14px;'>"
                f"<h3 style='color: #046d94; margin-bottom: 5px;'>📌 Orden: {row['ORDEN']}</h3>"
                f"<p><b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Código Postal:</b> {row['CP']}</p>"
                f"<p><b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Distancia:</b> {row['Distancia']:.2f} km</p>"
                f"</div>"
            )

            label = QLabel(texto_opcion)
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            label.setWordWrap(True)
            label.setStyleSheet("font-size: 15px; cursor: pointer;")

            label.mousePressEvent = lambda event, row=row: self.centrar_mapa_en_orden(row)

            self.result_layout.addWidget(label)

    def centrar_mapa_en_orden(self, row):
        m = folium.Map(location=[row["Latitud"], row["Longitud"]], zoom_start=12)

        if hasattr(self, "usuario_lat") and hasattr(self, "usuario_lon"):
            folium.Marker(
                [self.usuario_lat, self.usuario_lon],
                popup="""<div style="text-align: center; font-size: 16px; padding: 5px;">
                            <strong>Ubicación Usuario</strong>
                        </div>""",
                icon=folium.Icon(color="red")
            ).add_to(m)

        coordenadas_contador = {}

        for _, orden in self.ordenes_mostradas.iterrows():
            coords = (orden["Latitud"], orden["Longitud"])

            if coords in coordenadas_contador:
                coordenadas_contador[coords] += 1
            else:
                coordenadas_contador[coords] = 0

            adjusted_coords = get_adjusted_coords(coords, adjustment_factor=0.01, index=coordenadas_contador[coords])

            color = "green" if orden["ORDEN"] == row["ORDEN"] else "blue"

            popup_html = f"""
                <div style="text-align: center; font-size: 16px; padding: 5px;">
                    <strong>Orden:</strong> {orden['ORDEN']}<br>
                    <strong>Distancia:</strong> {orden['Distancia']:.2f} km
                </div>
            """

            popup = folium.Popup(popup_html, max_width=300, show=True if orden["ORDEN"] == row["ORDEN"] else False)

            folium.Marker(
                adjusted_coords,
                popup=popup,
                icon=folium.Icon(color=color)
            ).add_to(m)

        m.save(self.map_file)
        self.map_view.setUrl(QUrl.fromLocalFile(os.path.abspath(self.map_file)))

    def update_map(self, ordenes, lat_usuario, lon_usuario):
        m = folium.Map(location=[lat_usuario, lon_usuario], zoom_start=12)

        # Mantener el marcador rojo para la ubicación del usuario
        folium.Marker(
            [lat_usuario, lon_usuario],
            popup="""<div style="text-align: center; font-size: 16px; padding: 5px;">
                        <strong>Ubicación Usuario</strong>
                    </div>""",
            icon=folium.Icon(color="red")
        ).add_to(m)

        # Diccionario para contar coordenadas repetidas
        coordenadas_contador = {}

        # Generar los marcadores con ajuste de coordenadas
        for index, (_, row) in enumerate(ordenes.iterrows()):
            coords = (row["Latitud"], row["Longitud"])

            # Si la coordenada ya existe, aumentar su contador
            if coords in coordenadas_contador:
                coordenadas_contador[coords] += 1
            else:
                coordenadas_contador[coords] = 0

            # Aplicar desplazamiento usando la función get_adjusted_coords
            adjusted_coords = get_adjusted_coords(coords, adjustment_factor=0.01, index=coordenadas_contador[coords])

            popup_html = f"""
                <div style="text-align: center; font-size: 16px; padding: 5px;">
                    <strong>Orden:</strong> {row['ORDEN']}<br>
                    <strong>Distancia:</strong> {row['Distancia']:.2f} km
                </div>
            """

            folium.Marker(
                adjusted_coords,
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color="blue")
            ).add_to(m)

        # Guardar y actualizar el mapa
        m.save(self.map_file)
        self.map_view.setUrl(QUrl.fromLocalFile(os.path.abspath(self.map_file)))

