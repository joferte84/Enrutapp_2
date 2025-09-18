# modulos/utils.py
import os
import sys
import re
import glob
import json
import pandas as pd
from geopy.distance import geodesic
from rapidfuzz import process, fuzz

from modulos.api_manager import APIManager

from modulos.logger_config import logger, BASE_DIR, CONFIG_PATH

def cargar_configuracion():
    """
    Carga y valida los archivos de configuración necesarios para la aplicación, incluyendo:
    - Archivos de códigos postales, horarios técnicos y rutas de técnicos.
    - Asignación de códigos postales a técnicos con coincidencias exactas y aproximadas.
    Sobrescribe el archivo `ExportBase` con códigos postales asignados.
    Returns:
        dict: Diccionario con rutas de archivos de configuración cargados.
    """
    try:
        # Lista para rastrear valores sin coincidencia
        valores_no_coincidentes = []

        def limpiar_texto(texto):
            """
            Limpia el texto eliminando caracteres no deseados, como `_x000D_`, saltos de línea, etc.
            """
            if pd.isna(texto):  # Manejar valores nulos
                return ""
            texto = re.sub(r'_x000D_|[\n\r]+', '', texto)  # Eliminar `_x000D_` y saltos de línea
            texto = re.sub(r'\s+', ' ', texto).strip()  # Reemplazar múltiples espacios por uno y recortar
            return texto

        # Cargar el archivo de códigos postales
        archivo_codigos_postales = cargar_listado_codigos_postales(BASE_DIR)

        # Otros archivos y configuraciones
        carpeta_descargas = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(carpeta_descargas):
            raise FileNotFoundError(f"La carpeta de descargas no existe: {carpeta_descargas}")

        # Cargar los horarios desde la función auxiliar
        horarios_tecnicos = cargar_horarios_tecnicos(BASE_DIR)

        archivo_exportbase = encontrar_archivo_mas_reciente(carpeta_descargas, "ExportBase_*.xlsx")
        if not archivo_exportbase:
            raise FileNotFoundError("No se encontró ningún archivo 'ExportBase' válido en la carpeta de descargas.")

        archivo_cp_tecnicos_adt = encontrar_archivo_mas_reciente(carpeta_descargas, "CODIGOS POSTALES TECNICOS ADT*.xlsx")
        if not archivo_cp_tecnicos_adt:
            raise FileNotFoundError("No se encontró ningún archivo 'CODIGOS POSTALES TECNICOS ADT' válido en la carpeta de descargas.")

        # Cargar los archivos en DataFrames
        df_rutas_tecnicos = pd.read_excel(archivo_exportbase)
        cp_tecnicos_adt = pd.read_excel(archivo_cp_tecnicos_adt, sheet_name="Hoja1")

        # Excluir valores que comiencen por "Pendiente RECUR"
        df_rutas_tecnicos = df_rutas_tecnicos[~df_rutas_tecnicos['Res_Label'].str.startswith("Pendiente RECUR")]

        # Limpiar columnas relevantes
        df_rutas_tecnicos['Res_Label'] = df_rutas_tecnicos['Res_Label'].apply(limpiar_texto)
        cp_tecnicos_adt['Nombre Enrutador'] = cp_tecnicos_adt['Nombre Enrutador'].apply(limpiar_texto)

        # Verificar las columnas en cp_tecnicos_adt
        if 'Nombre Enrutador' not in cp_tecnicos_adt.columns or 'Codigo Postal' not in cp_tecnicos_adt.columns:
            raise KeyError("Las columnas 'Nombre Enrutador' y 'Codigo Postal' deben estar en el archivo de técnicos.")
        if 'Res_Label' not in df_rutas_tecnicos.columns:
            raise KeyError("La columna 'Res_Label' debe estar presente en el archivo de rutas.")

        # Crear un diccionario para facilitar la búsqueda
        mapping_tecnicos = dict(zip(cp_tecnicos_adt['Nombre Enrutador'], cp_tecnicos_adt['Codigo Postal']))

        def asignar_codigo_postal(res_label):
            # Buscar coincidencia exacta primero
            if res_label in mapping_tecnicos:
                return mapping_tecnicos[res_label]

            # Usar coincidencia aproximada si no se encuentra exacto
            coincidencia = process.extractOne(res_label, list(mapping_tecnicos.keys()), scorer=fuzz.token_sort_ratio)
            if coincidencia and coincidencia[1] >= 80:  # Umbral de similitud
                return mapping_tecnicos[coincidencia[0]]
            
            # Si no se encuentra coincidencia
            valores_no_coincidentes.append(res_label)  # Añadir a la lista
            return None

        # Aplicar la función y asignar los resultados
        df_rutas_tecnicos['Codigo Postal Asignado'] = df_rutas_tecnicos['Res_Label'].apply(asignar_codigo_postal)

        # Guardar los cambios en el archivo original
        df_rutas_tecnicos.to_excel(archivo_exportbase, index=False)

        return {
            'archivo_codigos_postales': archivo_codigos_postales,
            'archivo_excel': archivo_exportbase,
            'archivo_cp_tecnicos_adt': archivo_cp_tecnicos_adt,
            'archivo_horarios_tecnicos': horarios_tecnicos
        }

    except FileNotFoundError as e:
        logger.error("Error al cargar la configuración: %s", e)
        raise

    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        raise

def cargar_listado_codigos_postales(base_dir=BASE_DIR):
    """
    Carga el archivo `Listado-de-CP.xlsx` desde la ubicación especificada.
    Returns:
        str: Ruta del archivo `Listado-de-CP.xlsx`.
    Raises:
        FileNotFoundError: Si el archivo no existe.
    """
    """
    Carga el archivo Listado-de-CP.xlsx desde la ubicación correcta dependiendo del entorno.
    """
    try:
        # En entorno compilado (PyInstaller)
        if getattr(sys, "frozen", False):
            archivo_codigos_postales = os.path.join(BASE_DIR, "Enrutador", "_internal", "modulos", "data", "Listado-de-CP.xlsx")
        else:  # En entorno de desarrollo
            archivo_codigos_postales = os.path.join(BASE_DIR, "modulos", "data", "Listado-de-CP.xlsx")

        # Comprobar si el archivo existe
        if not os.path.exists(archivo_codigos_postales):
            raise FileNotFoundError(f"El archivo '{archivo_codigos_postales}' no fue encontrado.")

        return archivo_codigos_postales

    except Exception as e:
        logger.error(f"Error al cargar Listado-de-CP.xlsx: {e}")
        raise

def cargar_horarios_tecnicos(base_dir=BASE_DIR):
    """
    Carga el archivo `horarios_tecnicos.csv`, valida columnas necesarias y limpia los datos.
    Returns:
        pd.DataFrame: DataFrame con horarios de técnicos.
    Raises:
        FileNotFoundError: Si el archivo no existe.
        KeyError: Si faltan columnas críticas en el archivo.
    """
    try:
        # En entorno compilado (PyInstaller)
        if getattr(sys, "frozen", False):
            archivo_horarios_tecnicos = os.path.join(base_dir, "Enrutador", "_internal", "modulos", "data", "horarios_tecnicos.csv")
        else:  # En entorno de desarrollo
            archivo_horarios_tecnicos = os.path.join(base_dir, "modulos", "data", "horarios_tecnicos.csv")

        # Comprobar si el archivo existe
        if not os.path.exists(archivo_horarios_tecnicos):
            raise FileNotFoundError(f"El archivo '{archivo_horarios_tecnicos}' no fue encontrado.")

        # Cargar el archivo en un DataFrame
        df_horarios_tecnicos = pd.read_csv(archivo_horarios_tecnicos)

        # Verificar columnas críticas
        columnas_necesarias = ['Nombre_Tecnico', 'Horario_Inicio', 'Horario_Fin']
        for columna in columnas_necesarias:
            if columna not in df_horarios_tecnicos.columns:
                raise KeyError(f"La columna '{columna}' es obligatoria en el archivo horarios_tecnicos.csv.")

        # Limpieza y conversión de datos
        def limpiar_texto(texto):
            if pd.isna(texto):  # Manejar valores nulos
                return ""
            texto = re.sub(r'_x000D_|[\n\r]+', '', texto)  # Eliminar `_x000D_` y saltos de línea
            texto = re.sub(r'\s+', ' ', texto).strip()  # Reemplazar múltiples espacios por uno y recortar
            return texto

        # Limpiar nombres
        df_horarios_tecnicos['Nombre_Tecnico'] = df_horarios_tecnicos['Nombre_Tecnico'].apply(limpiar_texto)

        # Convertir horarios a formato datetime.time
        df_horarios_tecnicos['Horario_Inicio'] = pd.to_datetime(df_horarios_tecnicos['Horario_Inicio'], format='%H:%M').dt.time
        df_horarios_tecnicos['Horario_Fin'] = pd.to_datetime(df_horarios_tecnicos['Horario_Fin'], format='%H:%M').dt.time

        return df_horarios_tecnicos

    except Exception as e:
        logger.error(f"Error al cargar horarios_tecnicos.csv: {e}")
        raise

def encontrar_archivo_mas_reciente(carpeta, patron):
    """
    Encuentra el archivo más reciente que coincide con un patrón en una carpeta específica,
    eliminando archivos más antiguos excepto el más reciente y un backup.
    Args:
        carpeta (str): Ruta de la carpeta donde buscar archivos.
        patron (str): Patrón de búsqueda para los nombres de archivos.
    Returns:
        str: Ruta del archivo más reciente encontrado.
    """
    ruta_completa = os.path.join(carpeta, patron)
    archivos = glob.glob(ruta_completa)

    if not archivos:
        logger.warning("No se encontraron archivos que coincidan con el patrón: %s", patron)
        return None

    # Ordenar archivos por fecha de modificación (más reciente al inicio)
    archivos.sort(key=os.path.getmtime, reverse=True)

    # Mantener solo los dos archivos más recientes
    if len(archivos) > 2:
        for archivo in archivos[2:]:
            try:
                os.remove(archivo)
                logger.info("Archivo eliminado: %s", archivo)
            except Exception as e:
                logger.error("Error al intentar eliminar el archivo %s: %s", archivo, e)

    # Devolver el más reciente
    archivo_mas_reciente = archivos[0]
    return archivo_mas_reciente


def formatear_codigo_postal(cp):
    """
    Formatea un código postal para que tenga exactamente 5 dígitos, rellenando con ceros a la izquierda.
    Args:
        cp (str): Código postal a formatear.
    Returns:
        str: Código postal formateado o `None` si no es válido.
    """
    # Convertir a string y eliminar espacios en blanco
    cp = str(cp).strip()
    
    # Validar si el código postal es numérico
    if cp.isdigit():
        # Rellenar con ceros a la izquierda si tiene menos de 5 dígitos
        return cp.zfill(5)
    
    # Si no es válido, devolver None
    return None

def obtener_cp_de_direccion(direccion):
    """
    Extrae un código postal de una dirección utilizando expresiones regulares.
    Args:
        direccion (str): Dirección de texto de la cual extraer el código postal.
    Returns:
        str: Código postal extraído o `None` si no se encuentra.
    """
    match = re.search(r'\b\d{4,5}\b', str(direccion))
    return match.group() if match else None


def limpiar_direccion(direccion):
    if pd.isna(direccion):
        return ""
    direccion = str(direccion)  # Asegúrate de que sea una cadena
    match = re.search(r"\b\d{5}\b", direccion)
    return match.group() if match else None



def obtener_lat_lon_de_direccion(direccion, df_codigos_postales):
    """
    Obtiene latitud y longitud de una dirección basada en su código postal.
    Args:
        direccion (str): Dirección que contiene el código postal.
        df_codigos_postales (pd.DataFrame): DataFrame con datos de códigos postales, latitudes y longitudes.
    Returns:
        tuple: Latitud y longitud de la dirección o `(None, None)` si no se encuentran.
    """
    if not direccion:
        # Si la dirección es None o está vacía, retornamos None inmediatamente
        logger.warning("Dirección vacía o None recibida en obtener_lat_lon_de_direccion.")
        return None, None

    # Limpiar la dirección para extraer solo el código postal
    codigo_postal = limpiar_direccion(direccion)
    if codigo_postal:
        fila_cp = df_codigos_postales[df_codigos_postales['codigo_postal'] == codigo_postal]
        if not fila_cp.empty:
            lat, lon = fila_cp.iloc[0]['Latitud'], fila_cp.iloc[0]['Longitud']
            if pd.notnull(lat) and pd.notnull(lon):
                return lat, lon
            else:
                logger.warning(f"Coordenadas no válidas para el código postal {codigo_postal}.")

    return None, None

api_manager = APIManager()

def obtener_distancia_real(lat_anterior, lon_anterior, lat_nueva_visita, lon_nueva_visita):
    """
    Calcula la distancia real entre dos coordenadas geográficas utilizando la API seleccionada.
    Args:
        lat_anterior (float): Latitud del punto de origen.
        lon_anterior (float): Longitud del punto de origen.
        lat_nueva_visita (float): Latitud del punto de destino.
        lon_nueva_visita (float): Longitud del punto de destino.
    Returns:
        tuple: Distancia y duración del viaje o `(None, None)` si ocurre un error.
    """
    try:
        # Usar APIManager para obtener distancia y duración
        distancia_viaje, duracion_viaje = api_manager.obtener_distancia(
            lat_origen=lat_anterior,
            lon_origen=lon_anterior,
            lat_destino=lat_nueva_visita,
            lon_destino=lon_nueva_visita
        )

        # Verificar si se obtuvo una respuesta válida
        if distancia_viaje is not None and duracion_viaje is not None:
            return distancia_viaje, duracion_viaje
        else:
            logger.debug("[DEBUG] No se pudo calcular la distancia o duración")
            return None, None

    except Exception as e:
        logger.debug("[DEBUG] Error inesperado en obtener_distancia_real: {e}")
        return None, None


def calcular_distancia_haversine(lat1, lon1, lat2, lon2):
    """
    Calcula la distancia entre dos coordenadas usando Haversine.
    """
    if lat1 and lon1 and lat2 and lon2:
        return geodesic((lat1, lon1), (lat2, lon2)).kilometers
    return None

def cargar_credenciales(config_path=CONFIG_PATH):
    """
    Carga credenciales desde el archivo `config.json` y crea un archivo vacío si no existe.
    Args:
        config_path (str): Ruta del archivo de configuración `config.json`.
    Returns:
        dict: Diccionario con credenciales cargadas o vacío si ocurre un error.
    """
    try:
        # Asegurarse de que el directorio existe
        config_dir = os.path.dirname(config_path)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)

        # Crear archivo vacío si no existe
        if not os.path.exists(config_path):
            with open(config_path, "w") as file:
                json.dump({}, file)

        # Cargar las credenciales
        with open(config_path, "r") as file:
            return json.load(file)

    except json.JSONDecodeError:
        logger.info(f"Error: config.json está corrupto o mal formado en {config_path}.")
        return {}

    except Exception as e:
        logger.info(f"Error al cargar config.json: {e}")
        return {}

def guardar_credenciales(email, password, config_path=CONFIG_PATH):
    """
    Guarda un correo y contraseña en el archivo `config.json`, sobrescribiendo su contenido.
    Args:
        email (str): Correo electrónico del usuario.
        password (str): Contraseña del usuario.
        config_path (str): Ruta del archivo de configuración `config.json`.
    """
    try:
        credenciales = cargar_credenciales(config_path)
        credenciales[email] = password
        with open(config_path, "w") as file:
            json.dump(credenciales, file, indent=4)
    except Exception as e:
        logger.error(f"Error al guardar en config.json: {e}")
        raise

def obtener_archivo_unico(nombre_base="ARCHIVO UNICO", extension=".xlsx"):
    """
    Busca un archivo único en la carpeta de descargas que comienza con un nombre base y tiene una extensión específica.
    Si hay múltiples coincidencias, devuelve el archivo más reciente.
    Args:
        nombre_base (str): Prefijo del nombre del archivo.
        extension (str): Extensión del archivo.
    Returns:
        str: Ruta del archivo más reciente encontrado.
    """
    downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
    archivos = glob.glob(os.path.join(downloads_path, f"{nombre_base}*{extension}"))

    if not archivos:
        raise FileNotFoundError(f"No se encontró ningún archivo que comience con '{nombre_base}' en la carpeta Downloads.")
    
    # Seleccionar el archivo más reciente
    archivo_mas_reciente = max(archivos, key=os.path.getmtime)
    return archivo_mas_reciente

