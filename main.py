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
