import json
import os
import math
import csv
import shutil
import hashlib
import hmac
import secrets
import getpass
from copy import deepcopy
from datetime import datetime
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RUTA_PRODUCTOS = DATA_DIR / "productos.json"
RUTA_LOTES = DATA_DIR / "lotes.json"
RUTA_MOVIMIENTOS = DATA_DIR / "movimientos.json"
RUTA_VENTAS = DATA_DIR / "ventas.json"
SESION = None
ROL_ADMIN = "INSTRUCTOR/ADMINISTRADOR"

def cargar_json(ruta):
    """Carga una lista desde un archivo JSON. Si no existe, retorna []."""
    if not ruta.exists():
        return []
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = json.load(f)
            if not isinstance(contenido, list):
                raise ValueError(f"{ruta.name} debe contener una lista JSON.")
            return contenido
    except (json.JSONDecodeError, OSError) as error:
        raise ValueError(f"No se pudo leer {ruta.name}. Se conserva el archivo: {error}") from error



def guardar_json(ruta, datos):
    """Guarda una lista en un archivo JSON, creando la carpeta si hace falta."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(ruta.suffix + ".tmp")
    contenido = json.dumps(datos, ensure_ascii=False, indent=2, allow_nan=False)
    with open(temporal, "w", encoding="utf-8") as f:
        f.write(contenido + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporal, ruta)



def cargar_datos():
    """Carga las cuatro colecciones principales desde disco (RF17)."""
    diario = DATA_DIR / "transaccion.json"
    if diario.exists():
        with diario.open(encoding="utf-8") as archivo:
            pendiente = json.load(archivo)
        guardar_datos(pendiente, respaldar=False)
    return {
        "productos": cargar_json(RUTA_PRODUCTOS),
        "lotes": cargar_json(RUTA_LOTES),
        "movimientos": cargar_json(RUTA_MOVIMIENTOS),
        "ventas": cargar_json(RUTA_VENTAS),
    }



def crear_respaldo(rutas):
    existentes = [ruta for ruta in rutas if ruta.exists()]
    if not existentes:
        return
    destino = DATA_DIR / "backups" / (datetime.now().strftime("%Y%m%d_%H%M%S_%f") + secrets.token_hex(3))
    destino.mkdir(parents=True)
    for ruta in existentes:
        shutil.copy2(ruta, destino / ruta.name)



def guardar_datos(estado, respaldar=True):
    """Guarda las cuatro colecciones principales en disco (RF16)."""
    # Diario durable: si una escritura falla, la siguiente carga completa
    # la misma operación para no separar una venta de sus movimientos.
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if respaldar:
        crear_respaldo([RUTA_PRODUCTOS, RUTA_LOTES, RUTA_MOVIMIENTOS, RUTA_VENTAS])
    diario = DATA_DIR / "transaccion.json"
    guardar_json(diario, estado)
    guardar_json(RUTA_PRODUCTOS, estado["productos"])
    guardar_json(RUTA_LOTES, estado["lotes"])
    guardar_json(RUTA_MOVIMIENTOS, estado["movimientos"])
    guardar_json(RUTA_VENTAS, estado["ventas"])
    diario.unlink()
