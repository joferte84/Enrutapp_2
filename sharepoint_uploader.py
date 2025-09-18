# modulos/sharepoint_uploader.py

import json
import os
import sys
import requests
import pandas as pd
import io

from modulos.logger_config import get_data_dir, logger, get_base_dir

def get_config():
    """Lee las credenciales desde config.json y maneja su ubicación en entornos empaquetados."""
    config_path = os.path.join(get_data_dir(), "config.json")  

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"El archivo de configuración no se encuentra en: {config_path}")

    with open(config_path, "r") as f:
        return json.load(f)

def get_report_dir():
    """Devuelve la ruta del directorio donde se almacena el reporte (diferencia entre local y compilado)."""
    base_dir = get_base_dir()

    if getattr(sys, "frozen", False): 
        report_dir = os.path.join(base_dir, "Enrutador", "_internal", "modulos")
    else:  
        report_dir = os.path.join(base_dir, "modulos")

    logger.info(f" Directorio del reporte en uso: {report_dir}")
    return report_dir

def get_report_path():
    """Devuelve la ruta del reporte basada en si la aplicación está compilada o en desarrollo."""
    report_path = os.path.join(get_report_dir(), "reporte_log_binario.csv")

    # Log de depuración para asegurarnos de que se está usando la ruta correcta
    logger.info(f" Ruta del reporte en uso: {report_path}")
    
    return report_path


def get_access_token(config):
    """Obtiene un token OAuth2 usando MSAL para Microsoft Graph"""
    token_url = f"https://login.microsoftonline.com/{config['tenant_id']}/oauth2/v2.0/token"
    token_data = {
        'grant_type': 'client_credentials',
        'client_id': config['client_id'],
        'client_secret': config['client_secret'],
        'scope': 'https://graph.microsoft.com/.default'
    }

    response = requests.post(token_url, data=token_data)
    response_json = response.json()

    if 'access_token' in response_json:
        return response_json['access_token']
    else:
        return None

def get_site_id(access_token, site_name):
    """Obtiene el ID del sitio SharePoint usando Microsoft Graph"""
    tenant_domain = "activexservicios.sharepoint.com"  # Ajusta con tu dominio correcto
    url = f"https://graph.microsoft.com/v1.0/sites/{tenant_domain}:/sites/{site_name}"

    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(url, headers=headers)
    response_json = response.json()

    if 'id' in response_json:
        return response_json['id']
    else:
        return None

def upload_to_sharepoint():
    """Sube el CSV local al sitio SharePoint usando Graph API"""
    config = get_config()
    csv_path = get_report_path()

    access_token = get_access_token(config)
    if not access_token:
        return

    site_id = get_site_id(access_token, "desarrollo.contactcenter")
    if not site_id:
        return

    upload_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:/{config['sharepoint_folder']}/reporte_log_binario.csv:/content"
    headers = {'Authorization': f'Bearer {access_token}'}

    with open(csv_path, 'rb') as f:
        upload_response = requests.put(upload_url, headers=headers, data=f)

    if upload_response.status_code in [200, 201]:
        print("✅ Archivo subido/actualizado correctamente.")
    else:
        print(f" Error subiendo archivo: {upload_response.json()}")

def append_to_sharepoint_csv():
    """Añade los datos del CSV local al CSV remoto en SharePoint (Append) usando Graph API"""
    config = get_config()
    csv_path = get_report_path()

    if not os.path.exists(csv_path):
        logger.error(f" No se encontró el archivo CSV en: {csv_path}")
        return

    access_token = get_access_token(config)
    if not access_token:
        logger.error(" No se pudo obtener el token de acceso a SharePoint.")
        return

    site_id = get_site_id(access_token, "desarrollo.contactcenter")
    if not site_id:
        logger.error(" No se pudo obtener el ID del sitio de SharePoint.")
        return

    download_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:/{config['sharepoint_folder']}/reporte_log_binario.csv:/content"
    headers = {'Authorization': f'Bearer {access_token}'}

    # ✅ 1. Descargar CSV remoto
    download_response = requests.get(download_url, headers=headers)
    if download_response.status_code != 200:
        logger.error(f" No se pudo descargar el CSV remoto. Código: {download_response.status_code}")
        return

    remote_df = pd.read_csv(io.BytesIO(download_response.content))
    logger.info(f" CSV remoto descargado con {len(remote_df)} filas.")

    # ✅ 2. Leer CSV local
    local_df = pd.read_csv(csv_path)
    logger.info(f" CSV local leído con {len(local_df)} filas.")

    # ✅ 3. Combinar datos (Append) evitando duplicados
    combined_df = pd.concat([remote_df, local_df], ignore_index=True).drop_duplicates()
    logger.info(f" CSV combinado tiene {len(combined_df)} filas después de eliminar duplicados.")

    # ✅ 4. Guardar y volver a subir
    output_stream = io.BytesIO()
    combined_df.to_csv(output_stream, index=False)
    output_stream.seek(0)

    upload_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:/{config['sharepoint_folder']}/reporte_log_binario.csv:/content"
    upload_response = requests.put(upload_url, headers=headers, data=output_stream.read())

    if upload_response.status_code in [200, 201]:
        logger.info(" Archivo actualizado correctamente en SharePoint.")
    else:
        logger.error(f" Error subiendo archivo: {upload_response.json()}")
