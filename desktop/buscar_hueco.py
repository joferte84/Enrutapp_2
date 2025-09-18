# modulos/buscar_hueco.py
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QLabel, QLineEdit, QPushButton, QHBoxLayout, QScrollArea, QGroupBox

from PyQt5.QtCore import Qt

import pandas as pd
import re
from datetime import time, timedelta, datetime
from modulos.utils import (
    cargar_configuracion, obtener_lat_lon_de_direccion, calcular_distancia_haversine, 
    formatear_codigo_postal, obtener_cp_de_direccion, cargar_horarios_tecnicos,
    obtener_distancia_real
)
from modulos.logger_config import logger
from modulos.festivos import festivos, ciudades_a_comunidades
from modulos.api_manager import APIManager

api_manager = APIManager()

class BuscarHueco(QWidget):
    """
    Clase que implementa la funcionalidad de búsqueda de huecos disponibles para técnicos.

    Permite ingresar un código postal y una duración estimada para buscar huecos disponibles
    en los horarios de los técnicos más cercanos.
    """
        
    def __init__(self, parent=None):
        """
        Inicializa la clase BuscarHueco.

        Args:
            parent (QWidget, optional): Widget padre. Por defecto, None.
        """
        super().__init__(parent)
        self.init_ui()
        def limpiar_texto(texto):
            """
            Limpia el texto eliminando caracteres no deseados, como `_x000D_`, saltos de línea, etc.
            """
            if pd.isna(texto):  # Manejar valores nulos
                return ""
            texto = re.sub(r'_x000D_|[\n\r]+', '', texto)  # Eliminar `_x000D_` y saltos de línea
            texto = re.sub(r'\s+', ' ', texto).strip()  # Reemplazar múltiples espacios por uno y recortar
            return texto
        
        # Cargar configuración y archivos necesarios
        configuracion = cargar_configuracion()
        self.df_codigos_postales = pd.read_excel(configuracion['archivo_codigos_postales'])
        
        # Asegurar que todos los códigos postales en `df_codigos_postales` están en formato de cinco dígitos
        self.df_codigos_postales['codigo_postal'] = self.df_codigos_postales['codigo_postal'].apply(formatear_codigo_postal)
        
        # Cargar `cp_tecnicos_adt` y aplicar formateo en sus códigos postales
        self.cp_tecnicos_adt = pd.read_excel(configuracion['archivo_cp_tecnicos_adt'], sheet_name='Hoja1')
        self.cp_tecnicos_adt['Codigo Postal'] = self.cp_tecnicos_adt['Codigo Postal'].apply(formatear_codigo_postal)
        self.cp_tecnicos_adt['Nombre Enrutador'] = self.cp_tecnicos_adt['Nombre Enrutador'].apply(limpiar_texto)

        self.horarios_tecnicos = cargar_horarios_tecnicos()

        # Continuación de la inicialización
        self.rutas_tecnicos = pd.read_excel(configuracion['archivo_excel'])

        # Filtrar solo las filas donde 'Evt_Type' sea 'Tarea'
        self.rutas_tecnicos = self.rutas_tecnicos[self.rutas_tecnicos['Evt_Type'] == 'Tarea']
        
        self.rutas_tecnicos['Direcciones'] = self.rutas_tecnicos[['Evt_POBLACION', 'Evt_PROVINCIA']].apply(
            lambda x: ', '.join(x.fillna('').astype(str)), axis=1)
        
        self.rutas_tecnicos['Evt_Label'] = self.rutas_tecnicos['Evt_Label'].astype(str)

        
        self.todos_eventos = pd.read_excel(configuracion['archivo_excel'])
        self.todos_eventos = self.todos_eventos[self.todos_eventos['Evt_Type'].isin(['Tarea', 'Indisponibilidad'])]

        # Verificar columnas críticas
        columnas_criticas = ['Res_Label', 'Dat_StartDate' , 'Dat_EndDate',]
        for columna in columnas_criticas:
            if columna not in self.rutas_tecnicos.columns:
                logger.debug(f"[DEBUG] La columna {columna} no está presente en rutas_tecnicos")

    def init_ui(self):
        """
        Inicializa la interfaz de usuario para la funcionalidad de búsqueda de huecos.
        """
        self.setWindowTitle("Buscar Huecos Disponibles")
        self.resize(1000, 600)

        # Layout principal
        self.layout = QVBoxLayout()

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

        # Grupo para la entrada de búsqueda
        input_group = QGroupBox("")
        input_group.setStyleSheet("font-size: 12px; padding: 8px; border: 0px solid #1f618d;")
        input_layout = QHBoxLayout()
        input_layout.setAlignment(Qt.AlignRight)  # Alineación a la derecha


        self.codigo_postal_input = QLineEdit(self)
        self.codigo_postal_input.setPlaceholderText("Introduce código postal")
        self.codigo_postal_input.setFixedSize(400, 40)
        self.codigo_postal_input.setStyleSheet("font-size: 16px; border-radius: 5px; padding: 5px; border: 2px solid #046d94;")

        self.duracion_input = QLineEdit(self)
        self.duracion_input.setPlaceholderText("Duración estimada en horas (ej. 1.5)")
        self.duracion_input.setFixedSize(400, 40)
        self.duracion_input.setStyleSheet("font-size: 16px; border-radius: 5px; padding: 5px; border: 2px solid #046d94;")

        # Botón unificado
        self.unified_btn = QPushButton("Buscar", self)
        self.unified_btn.setFixedSize(250, 40)
        self.unified_btn.setStyleSheet(BUTTON_STYLE)
        self.unified_btn.clicked.connect(self.ejecutar_busquedas)

        input_layout.addWidget(self.codigo_postal_input)
        input_layout.addWidget(self.duracion_input)
        input_layout.addWidget(self.unified_btn)
        input_group.setLayout(input_layout)
        self.layout.addWidget(input_group)

        # Layout principal para los resultados
        results_layout = QHBoxLayout()

        # Grupo para la izquierda (Buscar Huecos)
        left_group = QGroupBox("Huecos Disponibles")
        left_group.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px; border: 0px solid #1f618d;")
        left_layout = QVBoxLayout()
        self.left_scroll_area = QScrollArea(self)
        self.left_scroll_area.setStyleSheet("background-color: white; border: none;")
        self.left_scroll_area.setWidgetResizable(True)
        self.left_result_container = QWidget()
        self.left_result_layout = QVBoxLayout(self.left_result_container)
        self.left_scroll_area.setWidget(self.left_result_container)
        left_layout.addWidget(self.left_scroll_area)
        left_group.setLayout(left_layout)
        results_layout.addWidget(left_group)

        # Grupo para la derecha (Días Libres del Técnico más Cercano)
        right_group = QGroupBox("Día Libre Más Cercano")
        right_group.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px; border: 0px solid #1f618d;")
        right_layout = QVBoxLayout()
        self.right_scroll_area = QScrollArea(self)
        self.right_scroll_area.setStyleSheet("background-color: white; border: none;")
        self.right_scroll_area.setWidgetResizable(True)
        self.right_result_container = QWidget()
        self.right_result_layout = QVBoxLayout(self.right_result_container)
        self.right_scroll_area.setWidget(self.right_result_container)
        right_layout.addWidget(self.right_scroll_area)
        right_group.setLayout(right_layout)
        results_layout.addWidget(right_group)

        # Añadir el layout de resultados al layout principal
        self.layout.addLayout(results_layout)

        # Etiqueta de estado
        self.status_label = QLabel(self)
        self.layout.addWidget(self.status_label)

        self.setLayout(self.layout)


    def limpiar_result_area(self, layout):
        """
        Limpia el área de resultados especificada.

        Args:
            layout (QVBoxLayout): Layout que se va a limpiar.
        """
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()


    def ejecutar_busquedas(self):
        """
        Ejecuta las búsquedas de huecos disponibles y días libres.

        Limpia las áreas de resultados y muestra los resultados correspondientes.
        """
        self.limpiar_result_area(self.left_result_layout)
        self.limpiar_result_area(self.right_result_layout)

        # Obtener valores introducidos por el usuario
        codigo_postal = self.codigo_postal_input.text().strip()
        duracion = self.duracion_input.text().strip()

        # Registrar el uso del botón "Buscar"
        logger.info(f"Búsqueda en 'Buscar Hueco' con Código Postal: {codigo_postal}, Duración: {duracion}")

        # Ejecutar búsqueda de huecos
        self.mostrar_huecos(self.left_result_layout)

        # Ejecutar búsqueda de días libres
        self.mostrar_cinco_dias_libres_mas_cercanos(self.right_result_layout)


    def mostrar_huecos(self, layout):
        """
        Muestra los huecos disponibles en el área de resultados proporcionada.

        Args:
            layout (QVBoxLayout): Layout donde se mostrarán los resultados.
        """
        direccion_nueva_visita = self.codigo_postal_input.text().strip()
        if not direccion_nueva_visita:
            label_error = QLabel("Error: Debes introducir un código postal.")
            layout.addWidget(label_error)
            return

        try:
            # Primero reemplazamos la coma por un punto y luego convertimos a float
            duracion_texto = self.duracion_input.text().strip().replace(',', '.')
            duracion_nueva_visita = float(duracion_texto)
            
            if duracion_nueva_visita <= 0:
                raise ValueError("La duración debe ser mayor que 0.")
        except ValueError:
            label_error = QLabel("Error: Debes introducir una duración válida en horas.")
            layout.addWidget(label_error)
            return
        
        # Obtener coordenadas y verificar datos
        cp_usuario = obtener_cp_de_direccion(direccion_nueva_visita)
        if cp_usuario:
            cp_usuario = formatear_codigo_postal(cp_usuario)
        else:
            label_error = QLabel("Error: No se encontró un código postal en la dirección proporcionada.")
            layout.addWidget(label_error)
            return

        if cp_usuario not in self.df_codigos_postales['codigo_postal'].values:
            label_error = QLabel("Error: Código postal no encontrado en la base de datos.")
            layout.addWidget(label_error)
            return

        lat_nueva_visita, lon_nueva_visita = obtener_lat_lon_de_direccion(direccion_nueva_visita, self.df_codigos_postales)
        if lat_nueva_visita is None or lon_nueva_visita is None:
            label_error = QLabel("Error: No se encontraron coordenadas para la dirección proporcionada.")
            layout.addWidget(label_error)
            return

        # Buscar y mostrar huecos
        opciones_huecos = self.buscar_huecos_disponibles(self.rutas_tecnicos, duracion_nueva_visita, lat_nueva_visita, lon_nueva_visita)
        if not opciones_huecos:
            label_no_result = QLabel("No se encontraron huecos disponibles.")
            layout.addWidget(label_no_result)
            return
        
        opciones_filtradas = self.filtrar_y_ordenar_por_proximidad(opciones_huecos, lat_nueva_visita, lon_nueva_visita, self.df_codigos_postales)

        # Limitar a mostrar solo los primeros cinco huecos disponibles
        if not opciones_filtradas:
            label_no_result = QLabel("No se encontraron opciones cercanas.")
            layout.addWidget(label_no_result)
        else:
            for opcion in opciones_filtradas[:5]:  # Solo toma los primeros cinco
                fecha_visita = opcion['hora_fin_anterior'].strftime('%d/%m/%Y')
                texto_opcion = (
                    f"<div style='border-radius: 10px; background-color: #f8f9fa; padding: 15px; margin: 10px 0; "
                    f"border: 1px solid #ccc; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); font-size: 14px;'>"
                    
                    f"<h3 style='color: #046d94; margin-bottom: 5px;'>📅 {fecha_visita}</h3>"
                    f"<p><b style='color: #046d94;'>&nbsp;&nbsp;&nbsp;&nbsp;👨‍🔧 Técnico:</b> {opcion['tecnico']} <span style='color: #888;'>({opcion['direccion_siguiente']})</span></p>"
                    f"<p><b style='color: #046d94;'>&nbsp;&nbsp;&nbsp;&nbsp;📍 Distancia:</b> {opcion['distancia']:.2f} km</p>"
                    f"<p><b style='color: #046d94;'>&nbsp;&nbsp;&nbsp;&nbsp;⏱️ Tiempo estimado:</b> {opcion.get('tiempo_estimado', 'N/A')} minutos</p>"

                    f"<p><b style='color: #046d94;'>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Ubicación Anterior:</b> {opcion['direccion_anterior']}</p>"
                    f"<p><b style='color: #046d94;'>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Ubicación Siguiente:</b> {opcion['direccion_siguiente']}</p>"

                    f"<p><b style='color: #046d94;'>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Hora de Fin de Visita Anterior:</b> {opcion['hora_fin_anterior'].strftime('%H:%M')}</p>"
                    f"<p><b style='color: #046d94;'>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Hora de Inicio de la Siguiente Visita:</b> "
                    f"{'🛑 FIN DE JORNADA' if opcion['hora_inicio_siguiente'].strftime('%H:%M') == '18:00' else opcion['hora_inicio_siguiente'].strftime('%H:%M')}</p>"
                    
                    f"</div>"
                )

                label_opcion = QLabel(texto_opcion)
                label_opcion.setTextInteractionFlags(Qt.TextSelectableByMouse)
                label_opcion.setWordWrap(True)
                label_opcion.setStyleSheet("font-size: 16px;")  
                layout.addWidget(label_opcion)


    def obtener_datos_nueva_visita(self, direccion_nueva_visita, duracion_nueva_visita, df_codigos_postales):
        """
    Obtiene las coordenadas y la duración de una nueva visita basada en la dirección proporcionada.
    Args:
        direccion_nueva_visita (str): Dirección de la nueva visita.
        duracion_nueva_visita (float): Duración estimada de la nueva visita en minutos.
        df_codigos_postales (pd.DataFrame): DataFrame que contiene códigos postales y sus coordenadas correspondientes.

    Returns:
        tuple: Coordenadas de la nueva visita (latitud, longitud) y duración. Si no se encuentran datos, retorna (None, None, None).
    """
        cp_usuario = obtener_cp_de_direccion(direccion_nueva_visita)
        if cp_usuario not in df_codigos_postales['codigo_postal'].values:
            return None, None, None

        fila_cp = df_codigos_postales[df_codigos_postales['codigo_postal'] == cp_usuario]
        if not fila_cp.empty:
            lat_nueva_visita = fila_cp.iloc[0]['Latitud']
            lon_nueva_visita = fila_cp.iloc[0]['Longitud']
            return lat_nueva_visita, lon_nueva_visita, duracion_nueva_visita

        return None, None, None

    def obtener_cp_predeterminado_tecnico(self, nombre_tecnico):
        """
    Obtiene el código postal predeterminado asignado a un técnico.
    Args:
        nombre_tecnico (str): Nombre del técnico.

    Returns:
        str: Código postal predeterminado del técnico. Si no se encuentra, retorna None.
    """
        fila = self.cp_tecnicos_adt[self.cp_tecnicos_adt['Nombre Enrutador'] == nombre_tecnico]
        if not fila.empty:
            codigo_postal = formatear_codigo_postal(fila.iloc[0]['Codigo Postal'])
            return codigo_postal
        return None

    def buscar_huecos_disponibles(self, rutas_tecnicos, duracion_nueva_visita, lat_nueva_visita, lon_nueva_visita):
        """
        Busca huecos disponibles en las rutas de técnicos considerando su horario de jornada y el fin de jornada a las 18:00 por defecto.

        Args:
            rutas_tecnicos (DataFrame): Datos de rutas de los técnicos.
            duracion_nueva_visita (float): Duración estimada de la nueva visita.
            lat_nueva_visita (float): Latitud de la nueva visita.
            lon_nueva_visita (float): Longitud de la nueva visita.

        Returns:
            list: Lista de huecos disponibles con detalles como técnico, distancia y horarios.
        """
        opciones_huecos = []
        duracion_con_desplazamiento = duracion_nueva_visita + 1  # Añadir 60 min adicionales para el desplazamiento

        # Filtrar técnicos excluyendo aquellos en estado "Pendiente RECUR"
        rutas_tecnicos = rutas_tecnicos[~rutas_tecnicos['Res_Label'].str.startswith('Pendiente RECUR', na=False)].copy()

        # Configurar horarios de comida
        inicio_comida = time(13, 30)
        fin_comida = time(15, 30)
        duracion_comida = timedelta(hours=1)

        # Asegurar que 'FechaHoraFin' está disponible
        if 'FechaHoraFin' not in rutas_tecnicos.columns:
            if {'Dat_StartDate', 'Dat_StartHour', 'Dat_Hours'}.issubset(rutas_tecnicos.columns):
                rutas_tecnicos['FechaHoraInicio'] = pd.to_datetime(
                    rutas_tecnicos['Dat_StartDate'].astype(str) + ' ' + rutas_tecnicos['Dat_StartHour'].astype(str)
                )
                rutas_tecnicos['FechaHoraFin'] = rutas_tecnicos['FechaHoraInicio'] + pd.to_timedelta(
                    rutas_tecnicos['Dat_Hours'], unit='h')
            else:
                logger.error("ERROR: No se puede calcular 'FechaHoraFin' porque faltan columnas necesarias.")
                return []

        # Procesar huecos entre citas
        for tecnico, visitas in rutas_tecnicos.groupby('Res_Label'):
            print(f"🔍 Evaluando técnico: {tecnico}, tiene {len(visitas)} visitas en fechas: {visitas['FechaHoraInicio'].dt.strftime('%Y-%m-%d').unique()}")

            # Obtener código postal del técnico
            codigo_postal_tecnico = self.obtener_cp_predeterminado_tecnico(tecnico)

            # Si no tiene código postal predeterminado, intentamos con su última visita
            if not codigo_postal_tecnico and not visitas.empty:
                codigo_postal_tecnico = visitas.iloc[-1].get('Evt_PROVINCIA', None)

            # Si sigue sin código postal, descartar este técnico
            if not codigo_postal_tecnico:
                print(f"⚠️ No se encontró código postal para el técnico {tecnico}. Omitiendo evaluación de hueco.")
                continue

            print(f"🔍 Comparando código postal técnico: {codigo_postal_tecnico} con la nueva visita: {formatear_codigo_postal(codigo_postal_tecnico)}")

            # Obtener coordenadas del técnico
            lat_tecnico, lon_tecnico = obtener_lat_lon_de_direccion(codigo_postal_tecnico, self.df_codigos_postales)
            if lat_tecnico is None or lon_tecnico is None:
                print(f"⚠️ No se encontraron coordenadas para el técnico {tecnico}. Omitiendo evaluación de hueco.")
                continue

            # Obtener horario del técnico desde el archivo horarios_tecnicos
            horario_tecnico = self.horarios_tecnicos[self.horarios_tecnicos['Nombre_Tecnico'].str.contains(tecnico, case=False, na=False, regex=False)]
            if not horario_tecnico.empty:
                inicio_jornada = horario_tecnico.iloc[0]['Horario_Inicio']
                fin_jornada = horario_tecnico.iloc[0]['Horario_Fin']
                if isinstance(inicio_jornada, str):
                    inicio_jornada = datetime.strptime(inicio_jornada, '%H:%M:%S').time()
                if isinstance(fin_jornada, str):
                    fin_jornada = datetime.strptime(fin_jornada, '%H:%M:%S').time()
            else:
                inicio_jornada = time(9, 0)  # Valor predeterminado
                fin_jornada = time(18, 0)    # Valor predeterminado

            print(f"🕒 Horario del técnico {tecnico}: {inicio_jornada} - {fin_jornada}")

            # Ordenar visitas por fecha
            visitas = visitas.sort_values('FechaHoraInicio').reset_index(drop=True)

            # Revisar huecos entre citas
            for i in range(len(visitas) - 1):
                hora_fin_actual = visitas.loc[i, 'FechaHoraFin']
                hora_inicio_siguiente = visitas.loc[i + 1, 'FechaHoraInicio']
                hueco_horas = (hora_inicio_siguiente - hora_fin_actual).total_seconds() / 3600

                if (hueco_horas > 0 and 
                    hora_fin_actual.date() == hora_inicio_siguiente.date() and
                    inicio_jornada <= hora_fin_actual.time() <= fin_jornada and
                    inicio_jornada <= hora_inicio_siguiente.time() <= fin_jornada):

                    if hora_fin_actual.time() < fin_comida and hora_inicio_siguiente.time() > inicio_comida:
                        tiempo_reducido = duracion_comida.total_seconds() / 3600
                        hueco_horas -= tiempo_reducido
                        if hueco_horas < duracion_con_desplazamiento:
                            continue

                    distancia_hasta_nueva_visita = calcular_distancia_haversine(lat_tecnico, lon_tecnico, lat_nueva_visita, lon_nueva_visita)
                    tiempo_hasta_nueva_visita = distancia_hasta_nueva_visita / 60

                    direccion_siguiente = visitas.loc[i + 1, 'Direcciones']
                    lat_siguiente, lon_siguiente = obtener_lat_lon_de_direccion(direccion_siguiente, self.df_codigos_postales)
                    if lat_siguiente is None or lon_siguiente is None:
                        continue

                    distancia_hasta_siguiente_visita = calcular_distancia_haversine(lat_nueva_visita, lon_nueva_visita, lat_siguiente, lon_siguiente)
                    tiempo_hasta_siguiente_visita = distancia_hasta_siguiente_visita / 60

                    tiempo_total_necesario = tiempo_hasta_nueva_visita + duracion_nueva_visita + tiempo_hasta_siguiente_visita

                    if hueco_horas >= tiempo_total_necesario:
                        opciones_huecos.append({
                            'tecnico': tecnico,
                            'direccion_anterior': visitas.loc[i, 'Direcciones'],
                            'direccion_siguiente': visitas.loc[i + 1, 'Direcciones'],
                            'hora_fin_anterior': hora_fin_actual,
                            'hora_inicio_siguiente': hora_inicio_siguiente,
                            'fecha': hora_fin_actual.strftime('%d/%m/%Y'),
                            'distancia': distancia_hasta_nueva_visita,
                            'Evt_ORDENSERVICIO': visitas.loc[i, 'Evt_ORDENSERVICIO']
                        })


            # Revisar hueco al final de la jornada
            if not visitas.empty:
                ultima_visita_fin = visitas.loc[len(visitas) - 1, 'FechaHoraFin']
                fin_de_jornada = datetime.combine(ultima_visita_fin.date(), fin_jornada)

                if ultima_visita_fin + timedelta(hours=duracion_con_desplazamiento) <= fin_de_jornada:
                    opciones_huecos.append({
                        'tecnico': tecnico,
                        'direccion_anterior': visitas.loc[len(visitas) - 1, 'Direcciones'],
                        'direccion_siguiente': "Casa",
                        'hora_fin_anterior': ultima_visita_fin,
                        'hora_inicio_siguiente': fin_de_jornada,
                        'fecha': ultima_visita_fin.strftime('%d/%m/%Y'),
                        'distancia': 0,
                        'Evt_ORDENSERVICIO': 'N/A'
                    })

        # Ordenar huecos por distancia
        opciones_huecos = sorted(opciones_huecos, key=lambda x: x['distancia'])

        return opciones_huecos


    def filtrar_y_ordenar_por_proximidad(self, opciones_huecos, lat_nueva_visita, lon_nueva_visita, df_codigos_postales, max_distancia_km=200, top_n=5):
        """
    Filtra y ordena opciones de huecos disponibles según la proximidad a una nueva visita.
    Args:
        opciones_huecos (list): Lista de opciones de huecos disponibles.
        lat_nueva_visita (float): Latitud de la nueva visita.
        lon_nueva_visita (float): Longitud de la nueva visita.
        df_codigos_postales (pd.DataFrame): DataFrame con códigos postales y coordenadas.
        max_distancia_km (float, optional): Distancia máxima en kilómetros para filtrar opciones. Por defecto, 200.
        top_n (int, optional): Número máximo de opciones a devolver. Por defecto, 5.

    Returns:
        list: Lista de opciones filtradas y ordenadas según la distancia calculada.
    """
        opciones_filtradas = []

        # Calcular distancia aproximada con Haversine para cada opción
        for opcion in opciones_huecos:
            lat_anterior, lon_anterior = obtener_lat_lon_de_direccion(opcion['direccion_anterior'], df_codigos_postales)

            if lat_anterior and lon_anterior:
                # Calcular la distancia aproximada con Haversine
                distancia_aproximada = calcular_distancia_haversine(lat_anterior, lon_anterior, lat_nueva_visita, lon_nueva_visita)

                # Filtrar solo las opciones dentro del rango de distancia máximo
                if distancia_aproximada <= max_distancia_km:
                    opcion['distancia'] = distancia_aproximada
                    opciones_filtradas.append(opcion)

        # Ordenar y seleccionar las cinco mejores opciones según la distancia calculada
        opciones_filtradas = sorted(opciones_filtradas, key=lambda x: x['distancia'])[:top_n]

        # Llamar a la API para obtener la distancia real y tiempo de viaje de las cinco mejores opciones
        for opcion in opciones_filtradas:
            lat_anterior, lon_anterior = obtener_lat_lon_de_direccion(opcion['direccion_anterior'], df_codigos_postales)
            if lat_anterior and lon_anterior:
                # Llamada a la API para obtener la distancia y duración precisas
                distancia_real, duracion_real = obtener_distancia_real(lat_anterior, lon_anterior, lat_nueva_visita, lon_nueva_visita)
                if distancia_real is not None and duracion_real is not None:
                    opcion['distancia_real'] = distancia_real
                    opcion['tiempo_estimado'] = round(duracion_real)

        # Reordenar según la distancia real
        opciones_filtradas = sorted(opciones_filtradas, key=lambda x: x.get('distancia_real', x['distancia']))

        return opciones_filtradas

 
    def obtener_coordenadas_tecnico(self, tecnico):
        """
    Obtiene las coordenadas del técnico a partir de su código postal.
    Args:
        tecnico (str): Nombre del técnico.

    Returns:
        tuple: Coordenadas (latitud, longitud) del técnico. Si no se encuentran datos, retorna (None, None).
    """
        fila_tecnico = self.cp_tecnicos_adt[self.cp_tecnicos_adt['Nombre Enrutador'] == tecnico]
        if fila_tecnico.empty:
            return None, None

        codigo_postal = fila_tecnico.iloc[0]['Codigo Postal']
        fila_cp = self.df_codigos_postales[self.df_codigos_postales['codigo_postal'] == codigo_postal]
        if fila_cp.empty:
            return None, None

        lat = fila_cp.iloc[0]['Latitud']
        lon = fila_cp.iloc[0]['Longitud']
        return lat, lon

    def encontrar_cinco_tecnicos_mas_cercanos_dia_libre(self, lat_nueva_visita, lon_nueva_visita):
        """
        Encuentra los cinco técnicos más cercanos con al menos cinco días libres próximos.
        Args:
            lat_nueva_visita (float): Latitud de la nueva visita.
            lon_nueva_visita (float): Longitud de la nueva visita.

        Returns:
            list: Lista con los cinco técnicos más cercanos, sus cinco días libres y la distancia calculada.
        """
        tecnicos_disponibles = []

        for tecnico in self.cp_tecnicos_adt['Nombre Enrutador'].unique():
            cp_predeterminado = self.obtener_cp_predeterminado_tecnico(tecnico)
            if not cp_predeterminado:
                continue

            lat_predeterminado, lon_predeterminado = obtener_lat_lon_de_direccion(cp_predeterminado, self.df_codigos_postales)
            if lat_predeterminado is None or lon_predeterminado is None:
                continue

            distancia = calcular_distancia_haversine(lat_nueva_visita, lon_nueva_visita, lat_predeterminado, lon_predeterminado)
            dias_libres_mas_cercanos = self.obtener_dias_libres(tecnico, num_dias=5)

            if dias_libres_mas_cercanos:
                tecnicos_disponibles.append((tecnico, dias_libres_mas_cercanos, distancia))

        # Ordenar técnicos por distancia y devolver los primeros cinco
        tecnicos_disponibles = sorted(tecnicos_disponibles, key=lambda x: x[2])[:5]

        return tecnicos_disponibles

    def mostrar_cinco_dias_libres_mas_cercanos(self, layout):
        """
        Muestra los cinco técnicos más cercanos con sus cinco días libres más próximos.
        Args:
            layout (QLayout): Layout donde se imprimirán los resultados.
        """
        direccion_nueva_visita = self.codigo_postal_input.text().strip()

        cp_usuario = obtener_cp_de_direccion(direccion_nueva_visita)
        if not cp_usuario or cp_usuario not in self.df_codigos_postales['codigo_postal'].values:
            layout.addWidget(QLabel("Error: Código postal no encontrado en la base de datos."))
            return

        cp_usuario = formatear_codigo_postal(cp_usuario)
        lat_nueva_visita, lon_nueva_visita = obtener_lat_lon_de_direccion(direccion_nueva_visita, self.df_codigos_postales)

        if lat_nueva_visita is None or lon_nueva_visita is None:
            layout.addWidget(QLabel("Error: No se encontraron coordenadas para la dirección proporcionada."))
            return

        tecnicos_mas_cercanos = self.encontrar_cinco_tecnicos_mas_cercanos_dia_libre(lat_nueva_visita, lon_nueva_visita)

        if tecnicos_mas_cercanos:
            for tecnico, dias_libres, distancia_a_cp in tecnicos_mas_cercanos:
                texto_opcion = (
                    f"<div style='border-radius: 10px; background-color: #f8f9fa; padding: 15px; margin: 10px 0; "
                    f"border: 1px solid #ccc; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); font-size: 14px;'>"
                    f"<h3 style='color: #046d94;'>👨‍🔧 Técnico: {tecnico}</h3>"
                    f"<p><b style='color: #333;'>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;📍 Distancia estimada:</b> {distancia_a_cp:.2f} km</p>"
                    f"<p><b style='color: #046d94;'>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;📅 Días libres más cercanos:</b></p>"
                )
                for dia in dias_libres:
                    texto_opcion += f"<p style='margin-left: 15px;'>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;🗓️ {dia.strftime('%d/%m/%Y')}</p>"

                texto_opcion += "</div>"

                label_opcion = QLabel(texto_opcion)
                label_opcion.setTextInteractionFlags(Qt.TextSelectableByMouse)
                label_opcion.setWordWrap(True)
                label_opcion.setStyleSheet("font-size: 16px;")
                layout.addWidget(label_opcion)
        else:
            layout.addWidget(QLabel("<b>No se encontraron técnicos con días libres cercanos.</b>"))

    def obtener_dias_libres(self, tecnico, num_dias=5):
        """
        Encuentra los primeros 'num_dias' días libres para un técnico basado en la presencia de eventos en su agenda.

        Args:
            tecnico (str): Nombre del técnico.
            num_dias (int): Número de días libres que queremos obtener.

        Returns:
            list: Lista con los días libres más cercanos del técnico.
        """
        # Filtrar eventos del técnico (Si hay cualquier fila con Res_Label == técnico, la fecha está ocupada)
        eventos_tecnico = self.todos_eventos[
            self.todos_eventos['Res_Label'].str.contains(tecnico, na=False, case=False, regex=False)
        ].copy()

        if 'Dat_StartDate' in eventos_tecnico.columns:
            eventos_tecnico['Dat_StartDate'] = pd.to_datetime(eventos_tecnico['Dat_StartDate'], errors='coerce')
        else:
            return []

        if eventos_tecnico['Dat_StartDate'].isnull().all():
            return []

        # **Cualquier fecha en Dat_StartDate donde Res_Label == técnico se considera ocupada**
        dias_ocupados = set(eventos_tecnico['Dat_StartDate'].dt.date.dropna())

        try:
            ciudad_tecnico = self.cp_tecnicos_adt.loc[
                self.cp_tecnicos_adt['Nombre Enrutador'].str.contains(tecnico, na=False, case=False, regex=False),
                'Zona'
            ].iloc[0]
        except IndexError:
            return []

        comunidad_autonoma = ciudades_a_comunidades.get(ciudad_tecnico.strip().lower(), None)
        if comunidad_autonoma:
            dias_festivos = set(festivos.get("Nacionales", []))
            dias_festivos.update(festivos.get(comunidad_autonoma, []))
            dias_festivos = {pd.to_datetime(f).date() for f in dias_festivos}
            dias_ocupados.update(dias_festivos)

        # Buscar los primeros `num_dias` días libres en los próximos 30 días
        dias_libres = []
        rango_fechas = pd.date_range(start=pd.Timestamp('today').normalize() + pd.Timedelta(days=1), periods=30).date

        for dia in rango_fechas:
            if dia.weekday() in (5, 6):  # Excluir fines de semana
                continue
            if dia not in dias_ocupados:
                dias_libres.append(dia)
                if len(dias_libres) >= num_dias:
                    break

        return dias_libres

