# logger_config.py
import logging
from logging.handlers import TimedRotatingFileHandler
import os
import sys

def get_base_dir():
    """Devuelve la ruta base del proyecto dependiendo del entorno."""
    if getattr(sys, "frozen", False):  # Si está empaquetado con PyInstaller
        return os.path.abspath(os.path.dirname(sys.executable))  # Carpeta donde está el ejecutable
    else:  # En desarrollo
        return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def get_data_dir():
    """
    Devuelve la ruta al directorio de datos del proyecto.

    - En un entorno empaquetado con PyInstaller, la ruta apunta a `Enrutador/_internal/modulos/data`.
    - En desarrollo, la ruta apunta a `modulos/data`.

    Returns:
        str: Ruta completa al directorio de datos.
    """    
    base_dir = get_base_dir()
    if getattr(sys, "frozen", False):
        return os.path.join(base_dir, "Enrutador", "_internal", "modulos", "data")
    else:
        return os.path.join(base_dir, "modulos", "data")

def get_log_dir():
    """ Devuelve la ruta de logs ('modulos/' en local, '_internal/modulos/' al compilar) """
    base_dir = get_base_dir()
    if getattr(sys, "frozen", False):
        return os.path.join(base_dir, "Enrutador", "_internal", "modulos")
    else:
        return os.path.join(base_dir, "modulos")

# Configuración de rutas
BASE_DIR = get_base_dir()
DATA_DIR = get_data_dir()
CONFIG_PATH = os.path.join(DATA_DIR, "credenciales.json")
LOG_DIR = get_log_dir()
LOG_FILE_PATH = os.path.join(LOG_DIR, "enrutador.log")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

# Configuración del logger y el handler
logger = logging.getLogger("EnrutadorLogger")
logger.setLevel(logging.DEBUG)

# Verificar si ya hay handlers para evitar duplicados
if not logger.handlers:
    log_handler = TimedRotatingFileHandler(LOG_FILE_PATH, when="W0", interval=1, backupCount=1)
    log_handler.setLevel(logging.DEBUG)  # Capturar logs DEBUG+
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)

    # También imprimir en la consola si es entorno de desarrollo
    if not getattr(sys, "frozen", False):  # Solo en modo desarrollo
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

logger.info(" Logger configurado correctamente")
logger.debug(f" Logs guardados en: {LOG_FILE_PATH}")