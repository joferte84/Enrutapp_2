from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchWindowException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import os
import time
import glob
from modulos.logger_config import logger

class ActualizarTecnicos:
    """
    Clase que encapsula la lógica para automatizar la descarga de un archivo desde SharePoint.

    Métodos principales:
        - iniciar_sesion: Realiza el proceso de login en SharePoint.
        - verificar_descarga_completa: Verifica que un archivo se haya descargado correctamente.
        - verificar_archivo_descargado: Obtiene el archivo descargado en la carpeta de destino.
        - descargar_excel: Descarga el archivo Excel desde la plataforma SharePoint.
    """
    def __init__(self, email, password, download_path=None):
        """
        Inicializa la clase con las credenciales y la ruta de descarga.

        Args:
            email (str): Correo electrónico del usuario.
            password (str): Contraseña del usuario.
            download_path (str, optional): Ruta donde se descargará el archivo. Por defecto, la carpeta Descargas del usuario.
        """
        self.email = email
        self.password = password
        self.download_path = download_path or os.path.join(os.path.expanduser("~"), "Downloads")
        self.url = "https://activexservicios.sharepoint.com/:x:/s/CAT/EQbDJzgBSIZHlgCQ-xPCJ18BtuGBmBkO9K6I-eF2QJL1-Q?e=aROQf3"

    def iniciar_sesion(self, driver):
        """
        Realiza el inicio de sesión en la plataforma SharePoint.

        Args:
            driver (webdriver): Instancia de Selenium WebDriver.

        Raises:
            RuntimeError: Si ocurre un error durante el inicio de sesión.
        """
        try:
            driver.get(self.url)
            time.sleep(2)

            # Campo de correo
            correo_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "i0116"))
            )
            if self.email.strip():
                correo_input.send_keys(self.email)
                correo_input.send_keys(Keys.RETURN)
            else:
                raise ValueError("El campo de correo está vacío. Por favor, proporcione un correo válido.")
            time.sleep(2)

            # Campo de contraseña
            password_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "i0118"))
            )
            if self.password.strip():
                password_input.send_keys(self.password)
                password_input.send_keys(Keys.RETURN)
            else:
                raise ValueError("El campo de contraseña está vacío. Proporcione una contraseña válida.")
            time.sleep(12)

            # Clic en "No" para no mantener la sesión iniciada
            try:
                mantener_sesion_btn = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.ID, "idBtn_Back"))
                )
                mantener_sesion_btn.click()
            except Exception as e:
                logger.warning(f"Error al interactuar con el botón 'No': {e}")
            time.sleep(3)
        except (NoSuchWindowException, WebDriverException):
            logger.error("El navegador se cerró accidentalmente. Reinicia el proceso.")
            raise RuntimeError("El navegador se cerró accidentalmente.")
        except Exception as e:
            logger.error(f"Error durante el inicio de sesión: {e}")
            raise RuntimeError(f"Error durante el inicio de sesión: {e}")

    def verificar_descarga_completa(self, timeout=30):
        """
        Verifica si un archivo Excel se descargó completamente dentro del tiempo especificado.

        Args:
            timeout (int): Tiempo máximo de espera en segundos.

        Returns:
            bool: True si se detecta el archivo descargado.

        Raises:
            TimeoutError: Si no se detecta el archivo dentro del tiempo límite.
        """
        for _ in range(timeout):
            if any(f.endswith(".xlsx") for f in os.listdir(self.download_path)):
                return True
            time.sleep(1)
        logger.error("La descarga no se completó dentro del tiempo esperado.")
        raise TimeoutError("La descarga no se completó dentro del tiempo esperado.")

    def verificar_archivo_descargado(self):
        """
        Obtiene el archivo descargado desde la carpeta de destino.

        Returns:
            str: Ruta completa del archivo descargado.

        Raises:
            FileNotFoundError: Si no se encuentra ningún archivo descargado.
        """
        archivos = glob.glob(os.path.join(self.download_path, "*.xlsx"))
        if archivos:
            return archivos[0]
        else:
            logger.error(f"No se encontraron archivos en {self.download_path}")
            raise FileNotFoundError(f"No se encontró el archivo descargado en {self.download_path}")

    def descargar_excel(self):
        """
        Ejecuta el flujo completo para descargar un archivo Excel desde SharePoint.

        Raises:
            Exception: Si ocurre algún error durante la descarga o procesamiento del archivo.
        """
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_experimental_option(
            "prefs", {
                "download.default_directory": self.download_path,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
        )

        driver = webdriver.Chrome(options=options)

        try:
            self.iniciar_sesion(driver)

            # Cambiar al iframe principal
            iframe = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
            driver.switch_to.frame(iframe)

            # Clic en los botones
            archivo_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "FileMenuFlyoutLauncher"))
            )
            archivo_btn.click()

            crear_copia_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@name='Crear una copia']"))
            )
            crear_copia_btn.click()

            descargar_copia_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@name='Descargar una copia']"))
            )
            descargar_copia_btn.click()

            # Verificar descarga
            time.sleep(5)  # Este tiempo es necesario para permitir que inicie la descarga
            self.verificar_descarga_completa()
            archivo_descargado = self.verificar_archivo_descargado()

        except Exception as e:
            raise

        finally:
            try:
                driver.quit()
                logger.info("El navegador se cerró correctamente.")
            except WebDriverException:
                logger.warning("El navegador ya estaba cerrado.")
