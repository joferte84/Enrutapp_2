# modulos/crear_csv.py
import re
import pandas as pd
import sys
import os

def get_base_dir():
    """ Devuelve la ruta base del proyecto """
    if getattr(sys, "frozen", False):
        return os.path.abspath(os.path.dirname(sys.executable))
    else:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def get_report_dir():
    """ Devuelve la ruta del reporte ('modulos/' en local, '_internal/modulos/' al compilar) """
    base_dir = get_base_dir()
    report_dir = os.path.join(base_dir, "Enrutador", "_internal", "modulos") if getattr(sys, "frozen", False) else os.path.join(base_dir, "modulos")
    
    # 📌 Asegurar que la carpeta de logs existe antes de intentar escribir
    os.makedirs(report_dir, exist_ok=True)
    
    return report_dir

class CSVGenerator:
    def __init__(self):
        self.report_dir = get_report_dir()
        self.log_file_path = os.path.join(self.report_dir, "enrutador.log")
        self.output_csv_path = os.path.join(self.report_dir, "reporte_log_binario.csv")

    def generar_csv(self):
        """
        Lee el archivo de logs y genera un CSV con los eventos detectados.
        """
        # 📌 Si el log no existe, se crea vacío y se continúa
        if not os.path.exists(self.log_file_path):
            with open(self.log_file_path, "w") as f:
                f.write("")  
            return  #

        # Expresión regular para detectar correos electrónicos
        email_pattern = re.compile(r"[\w\.-]+@[\w\.-]+")

        # Expresiones regulares ajustadas para identificar eventos
        patterns = {
            "ordenes_cercanas": re.compile(r" Cercanas'"),
            "ordenes_urgentes": re.compile(r" urgentes'"),
            "buscar_hueco": re.compile(r" Hueco'"),
            "mapa_actualizado": re.compile(r"actualizado el mapa"),
            "marcador_agregado": re.compile(r"'marcador'"),
            "api_detectada": re.compile(r"(API|distancia|calculó una distancia)", re.IGNORECASE)  # Ampliada
        }

        data = []
        current_email = None
        last_map_update_minute = set()  

        # Leer el archivo de logs y procesar cada línea
        with open(self.log_file_path, "r", encoding="ISO-8859-1", errors="ignore") as file:
            for line in file:
                match_fecha = re.match(r"(\d{4}-\d{2}-\d{2}) (\d{2}):(\d{2}):(\d{2}),(\d{3})", line)
                if match_fecha:
                    fecha, hora, minuto, segundo, milisegundos = match_fecha.groups()
                    timestamp_minute = f"{fecha} {hora}:{minuto}:{segundo}.{milisegundos}"  # Mantener solo hasta el minuto
                else:
                    continue

                # Extraer correo del agente
                match_correo = email_pattern.search(line)
                if match_correo:
                    current_email = match_correo.group(0)  # Guardar el correo detectado

                # Detectar si la línea menciona "API" o "distancia"
                api_detectada = 1 if patterns["api_detectada"].search(line) else 0

                # Añadir línea de evento 'api_detectada' independiente
                if api_detectada == 1:
                    data.append({
                        "fecha": fecha,
                        "hora": f"{hora}:{minuto}:{segundo}",
                        "correo": current_email if current_email else "Desconocido",
                        "órdenes_cercanas": 0,
                        "órdenes_urgentes": 0,
                        "buscar_hueco": 0,
                        "mapa_actualizado": 0,
                        "marcador_agregado": 0,
                        "api_detectada": 1
                    })

                # Crear una línea para cada evento detectado
                if patterns["ordenes_cercanas"].search(line):
                    data.append({
                        "fecha": fecha,
                        "hora": f"{hora}:{minuto}",
                        "correo": current_email if current_email else "Desconocido",
                        "órdenes_cercanas": 1,
                        "órdenes_urgentes": 0,
                        "buscar_hueco": 0,
                        "mapa_actualizado": 0,
                        "marcador_agregado": 0,
                        "api_detectada": api_detectada
                    })

                if patterns["ordenes_urgentes"].search(line):
                    data.append({
                        "fecha": fecha,
                        "hora": f"{hora}:{minuto}",
                        "correo": current_email if current_email else "Desconocido",
                        "órdenes_cercanas": 0,
                        "órdenes_urgentes": 1,
                        "buscar_hueco": 0,
                        "mapa_actualizado": 0,
                        "marcador_agregado": 0,
                        "api_detectada": api_detectada
                    })

                if patterns["buscar_hueco"].search(line):
                    data.append({
                        "fecha": fecha,
                        "hora": f"{hora}:{minuto}",
                        "correo": current_email if current_email else "Desconocido",
                        "órdenes_cercanas": 0,
                        "órdenes_urgentes": 0,
                        "buscar_hueco": 1,
                        "mapa_actualizado": 0,
                        "marcador_agregado": 0,
                        "api_detectada": api_detectada
                    })

                # Consolidación del mapa_actualizado dentro del mismo minuto
                if patterns["mapa_actualizado"].search(line):
                    if timestamp_minute not in last_map_update_minute:
                        last_map_update_minute.add(timestamp_minute)
                        data.append({
                            "fecha": fecha,
                            "hora": f"{hora}:{minuto}",
                            "correo": current_email if current_email else "Desconocido",
                            "órdenes_cercanas": 0,
                            "órdenes_urgentes": 0,
                            "buscar_hueco": 0,
                            "mapa_actualizado": 1,
                            "marcador_agregado": 0,
                            "api_detectada": api_detectada
                        })

                if patterns["marcador_agregado"].search(line):
                    data.append({
                        "fecha": fecha,
                        "hora": f"{hora}:{minuto}",
                        "correo": current_email if current_email else "Desconocido",
                        "órdenes_cercanas": 0,
                        "órdenes_urgentes": 0,
                        "buscar_hueco": 0,
                        "mapa_actualizado": 0,
                        "marcador_agregado": 1,
                        "api_detectada": api_detectada
                    })

        # Crear DataFrame
        df = pd.DataFrame(data)

        # Eliminar filas donde el correo sea "Desconocido"
        df = df[df["correo"] != "Desconocido"]

        df = df.drop_duplicates(
            subset=["fecha", "hora", "correo", "órdenes_cercanas", "órdenes_urgentes", "buscar_hueco", "mapa_actualizado", "marcador_agregado", "api_detectada"],
            keep="first"
        )

        # Guardar en CSV
        df.to_csv(self.output_csv_path, index=False, encoding="utf-8")
