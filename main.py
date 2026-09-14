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

def pedir_texto(mensaje, obligatorio=True):
    while True:
        valor = input(mensaje).strip()
        if valor or not obligatorio:
            return valor
        print("Este dato es obligatorio, intente de nuevo.")



def pedir_numero(mensaje, tipo=float, minimo=None, permitir_igual=True):
    """Pide un número validando tipo y un mínimo opcional (RF01, RF02, PF002)."""
    while True:
        entrada = input(mensaje).strip()
        try:
            valor = tipo(entrada)
        except ValueError:
            print("Debe ingresar un valor numérico válido.")
            continue
        if not math.isfinite(valor):
            print("Debe ingresar un número finito, no NaN ni infinito.")
            continue
        if minimo is not None:
            if permitir_igual and valor < minimo:
                print(f"El valor debe ser mayor o igual a {minimo}.")
                continue
            if not permitir_igual and valor <= minimo:
                print(f"El valor debe ser mayor a {minimo}.")
                continue
        return valor



def pedir_fecha(mensaje):
    while True:
        texto = pedir_texto(mensaje)
        try:
            fecha = datetime.strptime(texto, "%Y-%m-%d")
            if fecha.strftime("%Y-%m-%d") != texto:
                raise ValueError
            return texto
        except ValueError:
            print("Fecha inválida. Use YYYY-MM-DD y una fecha existente.")



def generar_id_secuencial(coleccion, prefijo, ancho=4):
    """Genera identificadores tipo M0001, V0001 (regla de negocio 9)."""
    numeros = [int(item["id"][len(prefijo):]) for item in coleccion
               if item["id"].startswith(prefijo) and item["id"][len(prefijo):].isdigit()]
    numero = max(numeros, default=0) + 1
    return f"{prefijo}{numero:0{ancho}d}"

def buscar_producto(productos, codigo):
    codigo = codigo.strip().upper()
    for p in productos:
        if p["codigo"] == codigo:
            return p
    return None



def registrar_producto(estado):
    """RF01: valida código único, precio > 0 y stock mínimo >= 0."""
    codigo = pedir_texto("Código del producto: ").upper()
    if buscar_producto(estado["productos"], codigo):
        print(f"Error: ya existe un producto con el código {codigo} (PF001).")
        return
    nombre = pedir_texto("Nombre: ")
    categoria = pedir_texto("Categoría: ")
    unidad = pedir_texto("Unidad de medida: ")
    precio = pedir_numero("Precio (> 0): ", tipo=float, minimo=0, permitir_igual=False)
    stock_minimo = pedir_numero("Stock mínimo (>= 0): ", tipo=int, minimo=0)

    producto = {
        "codigo": codigo,
        "nombre": nombre,
        "categoria": categoria,
        "unidad": unidad,
        "precio": precio,
        "stock_minimo": stock_minimo,
        "activo": True,
        "costo_unitario": None,
    }
    estado["productos"].append(producto)
    guardar_datos(estado)
    print(f"Producto {codigo} registrado correctamente.")



def listar_productos(estado, solo_activos=True):
    """RF02: lista productos activos y permite búsqueda por código o nombre."""
    termino = pedir_texto(
        "Buscar por código o parte del nombre (Enter para listar todos): ",
        obligatorio=False,
    ).upper()
    encontrados = []
    for p in estado["productos"]:
        if solo_activos and not p["activo"]:
            continue
        if termino and termino not in p["codigo"] and termino not in p["nombre"].upper():
            continue
        encontrados.append(p)

    if not encontrados:
        print("No se encontraron productos.")
        return encontrados

    print(f"\n{'Código':<8}{'Nombre':<20}{'Categoría':<15}{'Precio':>10}{'Stock mín.':>12}")
    for p in encontrados:
        print(f"{p['codigo']:<8}{p['nombre']:<20}{p['categoria']:<15}{p['precio']:>10}{p['stock_minimo']:>12}")
    return encontrados



def actualizar_producto(estado):
    """RF03: actualiza datos del producto sin cambiar el código."""
    codigo = pedir_texto("Código del producto a actualizar: ").upper()
    producto = buscar_producto(estado["productos"], codigo)
    if not producto:
        print("No existe un producto con ese código.")
        return
    print("Deje en blanco para conservar el valor actual.")
    nuevo_nombre = pedir_texto(f"Nombre [{producto['nombre']}]: ", obligatorio=False)
    if nuevo_nombre:
        producto["nombre"] = nuevo_nombre
    nueva_categoria = pedir_texto(f"Categoría [{producto['categoria']}]: ", obligatorio=False)
    if nueva_categoria:
        producto["categoria"] = nueva_categoria
    nueva_unidad = pedir_texto(f"Unidad [{producto['unidad']}]: ", obligatorio=False)
    if nueva_unidad:
        producto["unidad"] = nueva_unidad
    resp = pedir_texto(f"Nuevo precio [{producto['precio']}] (Enter para omitir): ", obligatorio=False)
    if resp:
        try:
            nuevo_precio = float(resp)
            if math.isfinite(nuevo_precio) and nuevo_precio > 0:
                producto["precio"] = nuevo_precio
            else:
                print("Precio inválido, se conserva el anterior (PF002).")
        except ValueError:
            print("Precio inválido, se conserva el anterior (PF002).")
    resp = pedir_texto(f"Nuevo stock mínimo [{producto['stock_minimo']}] (Enter para omitir): ", obligatorio=False)
    if resp:
        try:
            nuevo_min = int(resp)
            if nuevo_min >= 0:
                producto["stock_minimo"] = nuevo_min
            else:
                print("Stock mínimo inválido, se conserva el anterior.")
        except ValueError:
            print("Stock mínimo inválido, se conserva el anterior.")
    guardar_datos(estado)
    print("Producto actualizado.")



def desactivar_producto(estado):
    """RF04: desactiva sin eliminar físicamente (regla de negocio 2)."""
    codigo = pedir_texto("Código del producto a desactivar: ").upper()
    producto = buscar_producto(estado["productos"], codigo)
    if not producto:
        print("No existe un producto con ese código.")
        return
    if not producto["activo"]:
        print("El producto ya está inactivo.")
        return
    producto["activo"] = False
    guardar_datos(estado)
    print(f"Producto {codigo} desactivado. Su historial se conserva.")

def buscar_lote(lotes, id_lote):
    id_lote = id_lote.strip().upper()
    for lote in lotes:
        if lote["id_lote"] == id_lote:
            return lote
    return None



def registrar_lote(estado):
    """RF05: registra un lote asociado únicamente a un producto existente y activo."""
    id_lote = pedir_texto("ID del lote: ").upper()
    if buscar_lote(estado["lotes"], id_lote):
        print("Error: ya existe un lote con ese ID.")
        return
    codigo_producto = pedir_texto("Código del producto asociado: ").upper()
    producto = buscar_producto(estado["productos"], codigo_producto)
    if not producto:
        print("Error: el producto no existe.")
        return
    if not producto["activo"]:
        print("Error: el producto está inactivo, no puede asociarse a un lote nuevo.")
        return
    fecha_siembra = pedir_fecha("Fecha de siembra (YYYY-MM-DD): ")
    area_m2 = pedir_numero("Área en m² (> 0): ", tipo=float, minimo=0, permitir_igual=False)

    lote = {
        "id_lote": id_lote,
        "producto_codigo": codigo_producto,
        "fecha_siembra": fecha_siembra,
        "area_m2": area_m2,
        "cantidad_producida": 0,
        "estado": "EN_PRODUCCION",
    }
    estado["lotes"].append(lote)
    guardar_datos(estado)
    print(f"Lote {id_lote} registrado en estado EN_PRODUCCION.")



def cosechar_lote(estado):
    """RF06/RF07: cosecha un lote y genera una entrada automática (regla 5, PF003, PF004)."""
    id_lote = pedir_texto("ID del lote a cosechar: ").upper()
    lote = buscar_lote(estado["lotes"], id_lote)
    if not lote:
        print(f"Error: el lote {id_lote} no existe (PF003).")
        return
    if lote["estado"] != "EN_PRODUCCION":
        print(f"Error: el lote {id_lote} ya fue cosechado o está cancelado (PF004).")
        return
    cantidad = pedir_numero("Cantidad producida (> 0): ", tipo=float, minimo=0, permitir_igual=False)
    lote["cantidad_producida"] = cantidad
    lote["estado"] = "COSECHADO"
    registrar_movimiento(
        estado,
        lote["producto_codigo"],
        "ENTRADA",
        cantidad,
        f"Cosecha lote {id_lote}",
    )
    guardar_datos(estado)
    print(f"Lote {id_lote} cosechado. Se generó una entrada de inventario automática.")



def cancelar_lote(estado):
    """RF06: cambia el estado de un lote a CANCELADO."""
    id_lote = pedir_texto("ID del lote a cancelar: ").upper()
    lote = buscar_lote(estado["lotes"], id_lote)
    if not lote:
        print("El lote no existe.")
        return
    if lote["estado"] != "EN_PRODUCCION":
        print("Solo se pueden cancelar lotes en producción.")
        return
    lote["estado"] = "CANCELADO"
    guardar_datos(estado)
    print(f"Lote {id_lote} cancelado.")



def listar_lotes(estado):
    if not estado["lotes"]:
        print("No hay lotes registrados.")
        return
    print(f"\n{'ID':<8}{'Producto':<10}{'Siembra':<12}{'Área m²':>10}{'Producido':>12}{'Estado':>16}")
    for lote in estado["lotes"]:
        print(
            f"{lote['id_lote']:<8}{lote['producto_codigo']:<10}{lote['fecha_siembra']:<12}"
            f"{lote['area_m2']:>10}{lote['cantidad_producida']:>12}{lote['estado']:>16}"
        )

def calcular_stock(movimientos, codigo_producto):
    """Calcula el stock a partir de los movimientos (regla de negocio 3)."""
    stock = 0
    for m in movimientos:
        if m["producto_codigo"] != codigo_producto:
            continue
        if m["tipo"] == "ENTRADA":
            stock += m["cantidad"]
        elif m["tipo"] == "SALIDA":
            stock -= m["cantidad"]
    return stock



def registrar_movimiento(estado, codigo_producto, tipo, cantidad, motivo):
    """Crea un movimiento; la operación completa se persiste al confirmar."""
    if not buscar_producto(estado["productos"], codigo_producto):
        raise ValueError("El producto no existe.")
    if tipo not in ("ENTRADA", "SALIDA") or not math.isfinite(cantidad) or cantidad <= 0:
        raise ValueError("Tipo o cantidad de movimiento inválidos.")
    if not motivo.strip():
        raise ValueError("El motivo es obligatorio.")
    if tipo == "SALIDA" and cantidad > calcular_stock(estado["movimientos"], codigo_producto):
        raise ValueError("Stock insuficiente.")
    movimiento = {
        "id": generar_id_secuencial(estado["movimientos"], "M"),
        "producto_codigo": codigo_producto,
        "tipo": tipo,
        "cantidad": cantidad,
        "motivo": motivo,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    estado["movimientos"].append(movimiento)
    return movimiento



def entrada_manual(estado):
    """RF08: entrada manual de inventario con motivo obligatorio."""
    codigo = pedir_texto("Código del producto: ").upper()
    producto = buscar_producto(estado["productos"], codigo)
    if not producto or not producto["activo"]:
        print("Error: el producto no existe o está inactivo.")
        return
    cantidad = pedir_numero("Cantidad de entrada (> 0): ", tipo=float, minimo=0, permitir_igual=False)
    motivo = pedir_texto("Motivo (obligatorio): ")
    registrar_movimiento(estado, codigo, "ENTRADA", cantidad, motivo)
    guardar_datos(estado)
    print("Entrada registrada correctamente.")



def salida_manual(estado):
    """RF09: salida manual solo si existe stock suficiente (PF005)."""
    codigo = pedir_texto("Código del producto: ").upper()
    producto = buscar_producto(estado["productos"], codigo)
    if not producto or not producto["activo"]:
        print("Error: el producto no existe o está inactivo.")
        return
    stock_actual = calcular_stock(estado["movimientos"], codigo)
    cantidad = pedir_numero("Cantidad de salida (> 0): ", tipo=float, minimo=0, permitir_igual=False)
    if cantidad > stock_actual:
        print(f"Error: stock insuficiente (disponible: {stock_actual}) (PF005).")
        return
    motivo = pedir_texto("Motivo (obligatorio): ")
    registrar_movimiento(estado, codigo, "SALIDA", cantidad, motivo)
    guardar_datos(estado)
    print("Salida registrada correctamente.")



def listar_movimientos(estado):
    if not estado["movimientos"]:
        print("No hay movimientos registrados.")
        return
    print(f"\n{'ID':<8}{'Producto':<10}{'Tipo':<10}{'Cantidad':>10}  {'Motivo':<25}{'Fecha'}")
    for m in estado["movimientos"]:
        print(
            f"{m['id']:<8}{m['producto_codigo']:<10}{m['tipo']:<10}{m['cantidad']:>10}  "
            f"{m['motivo']:<25}{m['fecha']}"
        )
