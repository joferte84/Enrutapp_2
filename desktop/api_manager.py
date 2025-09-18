import csv
import random
import os
import requests
import openrouteservice
from modulos.logger_config import logger, get_data_dir


class APIManager:
    """
    Clase que gestiona las conexiones y operaciones con diferentes APIs de enrutamiento.

    Métodos principales:
        - cargar_apis_desde_csv: Carga configuraciones de API desde un archivo CSV.
        - seleccionar_api: Selecciona una API disponible basada en pesos configurados.
        - obtener_distancia: Calcula la distancia y duración entre dos coordenadas usando la API seleccionada.
    """

    def __init__(self, archivo_csv="api_keys.csv"):
        """
        Inicializa el APIManager con el archivo CSV de claves.

        Args:
            archivo_csv (str): Nombre del archivo CSV con las claves API.
        """
        self.api_keys_path = os.path.join(get_data_dir(), archivo_csv)
        self.apis = self.cargar_apis_desde_csv()

    def cargar_apis_desde_csv(self):
        """
        Carga las configuraciones de las APIs desde un archivo CSV.

        Returns:
            list: Lista de configuraciones de API cargadas.

        Raises:
            FileNotFoundError: Si el archivo CSV no se encuentra.
            Exception: Si ocurre un error durante la lectura del archivo.
        """
        apis = []
        try:
            if not os.path.exists(self.api_keys_path):
                raise FileNotFoundError(f"No se encontró el archivo de claves API en {self.api_keys_path}")

            with open(self.api_keys_path, mode="r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    apis.append({
                        "name": row["name"],
                        "key": row["key"],
                        "app_id": row.get("app_id", None),
                        "url": row["url"],
                        "weight": int(row["weight"]),
                    })
        except Exception as e:
            logger.error(f"[ERROR] No se pudo cargar el archivo CSV: {e}")
            raise
        return apis

    def seleccionar_api(self):
        """
        Selecciona una API basada en pesos configurados en el archivo CSV.

        Returns:
            dict: Configuración de la API seleccionada.
        """
        try:
            total_weight = sum(api["weight"] for api in self.apis)
            choice = random.uniform(0, total_weight)
            current = 0
            for api in self.apis:
                current += api["weight"]
                if current >= choice:
                    return api
        except Exception as e:
            logger.error(f"[ERROR] Error al seleccionar API: {e}")
        return self.apis[0]

    def obtener_distancia(self, lat_origen, lon_origen, lat_destino, lon_destino):
        """
        Calcula la distancia y duración entre dos coordenadas utilizando la API seleccionada.

        Args:
            lat_origen (float): Latitud de origen.
            lon_origen (float): Longitud de origen.
            lat_destino (float): Latitud de destino.
            lon_destino (float): Longitud de destino.

        Returns:
            tuple: Distancia en kilómetros y duración en minutos. Si ocurre un error, devuelve (None, None).
        """
        api = self.seleccionar_api()
        coords_origen = [lon_origen, lat_origen]
        coords_destino = [lon_destino, lat_destino]

        try:
            if api["name"] == "OpenRouteService":
                try:
                    client = openrouteservice.Client(key=api["key"])
                    ruta = client.directions(
                        coordinates=[coords_origen, coords_destino],
                        profile="driving-hgv",  # Para camiones
                        format="geojson",
                        radiuses=[5000, 5000]
                    )

                    distancia = ruta['features'][0]['properties']['segments'][0]['distance'] / 1000
                    duracion = ruta['features'][0]['properties']['segments'][0]['duration'] / 60
                    return distancia, duracion
                except openrouteservice.exceptions.ApiError as e:
                    logger.error(f"[ERROR] Error en OpenRouteService: {e}")
                except Exception as e:
                    logger.error(f"[ERROR] Error inesperado en OpenRouteService: {e}")
                return None, None

            elif api["name"] == "Here":
                params = {
                    "transportMode": "truck",  # Modo de transporte para camiones
                    "origin": f"{lat_origen},{lon_origen}",
                    "destination": f"{lat_destino},{lon_destino}",
                    "apiKey": api["key"],
                    "return": "summary",
                    "speedCap": 90  # Establece la velocidad máxima a 90 km/h
                }

                response = requests.get(api["url"], params=params)
                response.raise_for_status()
                ruta = response.json()
                distancia = ruta["routes"][0]["sections"][0]["summary"]["length"] / 1000
                duracion = ruta["routes"][0]["sections"][0]["summary"]["duration"] / 60
                return distancia, duracion

            elif api["name"] == "TomTom":
                url = f"{api['url']}/routing/1/calculateRoute/{lat_origen},{lon_origen}:{lat_destino},{lon_destino}/json"
                try:
                    response = requests.get(url, params={"key": api["key"]})
                    response.raise_for_status()
                    ruta = response.json()
                    distancia = ruta['routes'][0]['summary']['lengthInMeters'] / 1000
                    duracion = ruta['routes'][0]['summary']['travelTimeInSeconds'] / 60
                    return distancia, duracion
                except requests.exceptions.RequestException as e:
                    logger.error(f"[ERROR] Error en TomTom: {e}")
                    return None, None

        except requests.exceptions.RequestException as e:
            logger.error(f"[ERROR] Error en {api['name']}: {e}")
        except openrouteservice.exceptions.ApiError as e:
            logger.error(f"[ERROR] Error en OpenRouteService: {e}")
        except Exception as e:
            logger.error(f"[ERROR] Error inesperado en {api['name']}: {e}")

        return None, None
