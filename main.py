

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


def mostrar_tabla(encabezados, filas):
    if not filas:
        print("No hay registros para mostrar.")
        return
    datos = [[str(valor) for valor in fila] for fila in filas]
    columnas = []
    for indice, encabezado in enumerate(encabezados):
        ancho = len(str(encabezado))
        for fila in datos:
            ancho = max(ancho, len(fila[indice]))
        columnas.append(ancho)

    def formato_celda(valor, ancho, derecha=False):
        return f"{valor:>{ancho}}" if derecha else f"{valor:<{ancho}}"

    borde_superior = "┌" + "┬".join("─" * (ancho + 2) for ancho in columnas) + "┐"
    borde_medio = "├" + "┼".join("─" * (ancho + 2) for ancho in columnas) + "┤"
    borde_inferior = "└" + "┴".join("─" * (ancho + 2) for ancho in columnas) + "┘"

    print()
    print(borde_superior)
    print("│ " + " │ ".join(formato_celda(str(encabezado), columnas[i]) for i, encabezado in enumerate(encabezados)) + " │")
    print(borde_medio)
    for fila in datos:
        print("│ " + " │ ".join(formato_celda(fila[i], columnas[i], derecha=(i > 0 and i >= 3)) for i in range(len(encabezados))) + " │")
    print(borde_inferior)


def cargar_json(ruta):
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
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(ruta.suffix + ".tmp")
    contenido = json.dumps(datos, ensure_ascii=False, indent=2, allow_nan=False)
    with open(temporal, "w", encoding="utf-8") as f:
        f.write(contenido + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporal, ruta)



def cargar_datos():
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



def formatear_moneda(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return "$0.00"
    return f"${numero:,.2f}"



def pedir_numero(mensaje, tipo=float, minimo=None, permitir_igual=True):
    while True:
        entrada = input(mensaje).strip()
        if tipo is float and entrada.startswith("$"):
            entrada = entrada[1:]
        entrada = entrada.replace(",", "")
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
    codigo = pedir_texto("Código del producto: ").upper()
    if buscar_producto(estado["productos"], codigo):
        print(f"Error: ya existe un producto con el código {codigo} (PF001).")
        return
    nombre = pedir_texto("Nombre: ")
    categoria = pedir_texto("Categoría: ")
    unidad = pedir_texto("Unidad de medida: ")
    precio = pedir_numero("Precio (> 0) [$]: ", tipo=float, minimo=0, permitir_igual=False)
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

    mostrar_tabla(
        ["Código", "Nombre", "Categoría", "Precio", "Stock mín."],
        [
            [p["codigo"], p["nombre"], p["categoria"], formatear_moneda(p["precio"]), p["stock_minimo"]]
            for p in encontrados
        ],
    )
    return encontrados



def actualizar_producto(estado):
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
    resp = pedir_texto(f"Nuevo precio [{formatear_moneda(producto['precio'])}] (Enter para omitir): ", obligatorio=False)
    if resp:
        try:
            nuevo_precio = float(resp.replace("$", "").replace(",", ""))
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
    mostrar_tabla(
        ["ID", "Producto", "Siembra", "Área m²", "Producido", "Estado"],
        [
            [lote["id_lote"], lote["producto_codigo"], lote["fecha_siembra"], lote["area_m2"], lote["cantidad_producida"], lote["estado"]]
            for lote in estado["lotes"]
        ],
    )



def calcular_stock(movimientos, codigo_producto):
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
    mostrar_tabla(
        ["ID", "Producto", "Tipo", "Cantidad", "Motivo", "Fecha"],
        [
            [m["id"], m["producto_codigo"], m["tipo"], m["cantidad"], m["motivo"], m["fecha"]]
            for m in estado["movimientos"]
        ],
    )



def registrar_venta(estado):
    items = []
    print("Agregue los productos de la venta (código vacío para finalizar).")
    while True:
        codigo = pedir_texto("Código del producto (Enter para terminar): ", obligatorio=False).upper()
        if not codigo:
            break
        producto = buscar_producto(estado["productos"], codigo)
        if not producto or not producto["activo"]:
            print("Error: el producto no existe o está inactivo.")
            continue
        stock_disponible = calcular_stock(estado["movimientos"], codigo)
        ya_agregado = sum(i["cantidad"] for i in items if i["codigo"] == codigo)
        cantidad = pedir_numero("Cantidad (> 0): ", tipo=float, minimo=0, permitir_igual=False)
        if cantidad + ya_agregado > stock_disponible:
            print(
                f"Error: no se puede vender más de lo disponible "
                f"(disponible: {stock_disponible - ya_agregado})."
            )
            continue
        items.append(
            {
                "codigo": codigo,
                "cantidad": cantidad,
                "precio_unitario": producto["precio"],
                "costo_unitario": producto.get("costo_unitario"),
            }
        )
        print(f"Producto {codigo} agregado a la venta.")

    if not items:
        print("Error: una venta debe contener al menos un ítem válido (regla 6).")
        return

    total = sum(i["cantidad"] * i["precio_unitario"] for i in items)
    venta = {
        "id": generar_id_secuencial(estado["ventas"], "V"),
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "items": items,
        "total": total,
    }

    consolidado = {}
    for item in items:
        consolidado[item["codigo"]] = consolidado.get(item["codigo"], 0) + item["cantidad"]
    for codigo, cantidad_total in consolidado.items():
        disponible = calcular_stock(estado["movimientos"], codigo)
        if cantidad_total > disponible:
            print(f"Error: stock insuficiente para {codigo}, venta cancelada.")
            return

    for item in items:
        registrar_movimiento(
            estado,
            item["codigo"],
            "SALIDA",
            item["cantidad"],
            f"Venta {venta['id']}",
        )

    estado["ventas"].append(venta)
    guardar_datos(estado)
    print(f"Venta {venta['id']} registrada. Total: {formatear_moneda(total)}")



def consultar_ventas(estado):
    if not estado["ventas"]:
        print("No hay ventas registradas.")
        return
    for v in estado["ventas"]:
        print(f"\nVenta {v['id']} - {v['fecha']} - Total: {formatear_moneda(v['total'])} - {v.get('estado', 'VIGENTE')}")
        mostrar_tabla(
            ["Código", "Cantidad", "Precio", "Subtotal"],
            [
                [item["codigo"], item["cantidad"], formatear_moneda(item["precio_unitario"]), formatear_moneda(item["cantidad"] * item["precio_unitario"])]
                for item in v["items"]
            ],
        )



def alertas_stock(estado):
    alertas = []
    for p in estado["productos"]:
        if not p["activo"]:
            continue
        stock = calcular_stock(estado["movimientos"], p["codigo"])
        if stock <= p["stock_minimo"]:
            alertas.append((p, stock))

    if not alertas:
        print("No hay alertas de stock en este momento.")
        return

    mostrar_tabla(
        ["Código", "Nombre", "Stock", "Stock mín."],
        [[p["codigo"], p["nombre"], stock, p["stock_minimo"]] for p, stock in alertas],
    )



def reporte_inventario(estado):
    filas = []
    valor_total = 0
    for p in estado["productos"]:
        stock = calcular_stock(estado["movimientos"], p["codigo"])
        valor = stock * p["precio"]
        valor_total += valor
        filas.append([p["codigo"], p["nombre"], stock, valor])

    mostrar_tabla(["Código", "Nombre", "Stock", "Valor total"], [[codigo, nombre, stock, formatear_moneda(valor)] for codigo, nombre, stock, valor in filas])
    print(f"\nValor total del inventario: {formatear_moneda(valor_total)}")



def reporte_ventas(estado):
    vigentes = [v for v in estado["ventas"] if v.get("estado") != "DEVUELTA"]
    num_ventas = len(vigentes)
    unidades = sum(item["cantidad"] for v in vigentes for item in v["items"])
    ingresos = sum(v["total"] for v in vigentes)
    mostrar_tabla(
        ["Indicador", "Valor"],
        [["Número de ventas", num_ventas], ["Unidades vendidas", unidades], ["Ingresos acumulados", formatear_moneda(ingresos)]],
    )



def ranking_productos_vendidos(estado):
    totales = {}
    for v in estado["ventas"]:
        if v.get("estado") == "DEVUELTA":
            continue
        for item in v["items"]:
            totales[item["codigo"]] = totales.get(item["codigo"], 0) + item["cantidad"]

    if not totales:
        print("Aún no hay ventas registradas.")
        return

    ranking = sorted(totales.items(), key=lambda x: x[1], reverse=True)[:3]
    mostrar_tabla(
        ["Posición", "Código", "Nombre", "Unidades"],
        [
            [
                posicion,
                codigo,
                buscar_producto(estado["productos"], codigo)["nombre"] if buscar_producto(estado["productos"], codigo) else codigo,
                cantidad,
            ]
            for posicion, (codigo, cantidad) in enumerate(ranking, start=1)
        ],
    )



def reporte_rotacion_productos(estado):
    salidas_por_producto = {}
    for m in estado["movimientos"]:
        if m["tipo"] == "SALIDA":
            salidas_por_producto[m["producto_codigo"]] = (
                salidas_por_producto.get(m["producto_codigo"], 0) + m["cantidad"]
            )

    if not salidas_por_producto:
        print("Aún no hay salidas de inventario registradas.")
        return

    filas = []
    for codigo, total_salidas in salidas_por_producto.items():
        producto = buscar_producto(estado["productos"], codigo)
        nombre = producto["nombre"] if producto else codigo
        stock_actual = calcular_stock(estado["movimientos"], codigo)
        base = stock_actual + total_salidas
        rotacion = (total_salidas / base) if base > 0 else 0
        filas.append((codigo, nombre, total_salidas, stock_actual, rotacion))

    filas.sort(key=lambda f: f[4], reverse=True)
    mostrar_tabla(
        ["Código", "Nombre", "Salidas", "Stock", "Rotación"],
        [[codigo, nombre, total_salidas, stock_actual, f"{rotacion:.0%}"] for codigo, nombre, total_salidas, stock_actual, rotacion in filas],
    )



def reporte_lotes(estado):
    filas = []
    for situacion in ("EN_PRODUCCION", "COSECHADO", "CANCELADO"):
        lotes = [l for l in estado["lotes"] if l["estado"] == situacion]
        filas.append([situacion, len(lotes), f"{sum(l['area_m2'] for l in lotes):g} m²"])
    for producto in estado["productos"]:
        cantidad = sum(l["cantidad_producida"] for l in estado["lotes"]
                       if l["producto_codigo"] == producto["codigo"] and l["estado"] == "COSECHADO")
        filas.append([f"{producto['codigo']} - {producto['nombre']}", f"{cantidad:g} {producto['unidad']}", "Cosechadas"])
    mostrar_tabla(["Concepto", "Cantidad", "Detalle"], filas)



def consultar_ventas_por_fecha(estado):
    inicio = pedir_fecha("Fecha inicial (YYYY-MM-DD): ")
    fin = pedir_fecha("Fecha final (YYYY-MM-DD): ")
    if fin < inicio:
        print("La fecha final no puede ser anterior a la inicial.")
        return
    filtradas = [v for v in estado["ventas"] if inicio <= v["fecha"][:10] <= fin]
    consultar_ventas({"ventas": filtradas})



def configurar_costo(estado):
    producto = buscar_producto(estado["productos"], pedir_texto("Código del producto: "))
    if not producto:
        print("No existe el producto.")
        return
    producto["costo_unitario"] = pedir_numero("Costo unitario (>= 0) [$]: ", minimo=0)
    guardar_datos(estado)
    print("Costo actualizado. Las ventas anteriores conservan su costo histórico.")



def reporte_utilidad(estado):
    ingresos = costos = 0
    sin_costo = 0
    for venta in estado["ventas"]:
        if venta.get("estado") == "DEVUELTA":
            continue
        for item in venta["items"]:
            costo = item.get("costo_unitario")
            if costo is None:
                sin_costo += 1
                continue
            ingresos += item["cantidad"] * item["precio_unitario"]
            costos += item["cantidad"] * costo
    print(f"Ingresos con costo conocido: {formatear_moneda(ingresos)}")
    print(f"Costo estimado: {formatear_moneda(costos)}")
    print(f"Utilidad estimada: {formatear_moneda(ingresos - costos)}")
    print(f"Ítems históricos excluidos por costo desconocido: {sin_costo}")
    print("Estimación de margen bruto; no incluye gastos, impuestos ni otros costos.")



def devolver_venta(estado):
    codigo = pedir_texto("ID de la venta a devolver: ").upper()
    venta = next((v for v in estado["ventas"] if v["id"] == codigo), None)
    if not venta:
        print("No existe la venta.")
        return
    if venta.get("estado") == "DEVUELTA":
        print("La venta ya fue devuelta.")
        return
    motivo = pedir_texto("Motivo de la devolución total: ")
    nuevo = deepcopy(estado)
    for item in venta["items"]:
        registrar_movimiento(nuevo, item["codigo"], "ENTRADA", item["cantidad"], f"Devolución {codigo}: {motivo}")
    registro = next(v for v in nuevo["ventas"] if v["id"] == codigo)
    registro.update(estado="DEVUELTA", motivo_devolucion=motivo,
                    fecha_devolucion=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    guardar_datos(nuevo)
    estado.update(nuevo)
    print(f"Venta {codigo} devuelta. Inventario reintegrado; historial conservado.")



def exportar_inventario_csv(estado):
    carpeta = DATA_DIR / "exportaciones"
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / ("inventario_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".csv")
    with ruta.open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.writer(archivo, delimiter=";")
        escritor.writerow(["codigo", "nombre", "unidad", "activo", "stock", "precio", "valor"])
        for p in estado["productos"]:
            stock = calcular_stock(estado["movimientos"], p["codigo"])
            textos = [str(p[c]) for c in ("codigo", "nombre", "unidad")]
            textos = ["'" + t if t.lstrip().startswith(("=", "+", "-", "@")) else t for t in textos]
            escritor.writerow(textos + [p["activo"], stock, f"${p['precio']:,.2f}", f"${stock * p['precio']:,.2f}"])
    print(f"Inventario exportado: {ruta}")
    return ruta



def es_administrador():
    return SESION is not None and SESION["rol"] == ROL_ADMIN



def requiere_admin(funcion, estado):
    if not es_administrador():
        print("Acceso denegado. Se requiere el rol INSTRUCTOR/ADMINISTRADOR.")
        return
    funcion(estado)



def guardar_usuario(usuarios, nombre, clave, rol):
    nombre = nombre.strip().lower()
    if not nombre or any(u["usuario"] == nombre for u in usuarios):
        raise ValueError("Usuario vacío o duplicado.")
    if len(clave) < 8 or rol not in ("OPERADOR", ROL_ADMIN):
        raise ValueError("La contraseña debe tener al menos 8 caracteres y el rol debe ser válido.")
    sal = secrets.token_hex(16)
    derivada = hashlib.pbkdf2_hmac("sha256", clave.encode(), bytes.fromhex(sal), 600000).hex()
    ruta = DATA_DIR / "usuarios.json"
    crear_respaldo([ruta])
    guardar_json(ruta, usuarios + [{"usuario": nombre, "rol": rol, "sal": sal, "hash": derivada}])



def autenticar(usuarios, nombre, clave):
    usuario = next((u for u in usuarios if u["usuario"] == nombre.strip().lower()), None)
    if usuario is None:
        return None
    derivada = hashlib.pbkdf2_hmac("sha256", clave.encode(), bytes.fromhex(usuario["sal"]), 600000).hex()
    if hmac.compare_digest(derivada, usuario["hash"]) and usuario["rol"] in ("OPERADOR", ROL_ADMIN):
        return {"usuario": usuario["usuario"], "rol": usuario["rol"]}
    return None



def iniciar_sesion():
    usuarios = cargar_json(DATA_DIR / "usuarios.json")
    if not usuarios:
        print("Primera ejecución: cree la cuenta INSTRUCTOR/ADMINISTRADOR.")
        nombre = pedir_texto("Nuevo usuario administrador: ")
        clave = getpass.getpass("Contraseña (mínimo 8 caracteres): ")
        if clave != getpass.getpass("Confirme la contraseña: "):
            print("Las contraseñas no coinciden.")
            return None
        guardar_usuario(usuarios, nombre, clave, ROL_ADMIN)
        usuarios = cargar_json(DATA_DIR / "usuarios.json")
    for _ in range(3):
        nombre = pedir_texto("Usuario: ")
        sesion = autenticar(usuarios, nombre, getpass.getpass("Contraseña: "))
        if sesion:
            print(f"Sesión iniciada: {sesion['usuario']} ({sesion['rol']})")
            return sesion
        print("Credenciales incorrectas.")
    return None



def crear_usuario(estado):
    usuarios = cargar_json(DATA_DIR / "usuarios.json")
    nombre = pedir_texto("Nuevo usuario: ")
    rol = pedir_texto("Rol (1 OPERADOR, 2 INSTRUCTOR/ADMINISTRADOR): ")
    if rol not in ("1", "2"):
        print("Rol inválido.")
        return
    clave = getpass.getpass("Contraseña (mínimo 8 caracteres): ")
    if clave != getpass.getpass("Confirme la contraseña: "):
        print("Las contraseñas no coinciden.")
        return
    guardar_usuario(usuarios, nombre, clave, "OPERADOR" if rol == "1" else ROL_ADMIN)
    print("Usuario creado.")



def menu_ampliaciones(estado):
    opciones = {"1": consultar_ventas_por_fecha, "2": reporte_utilidad, "3": exportar_inventario_csv}
    administrativas = {"4": configurar_costo, "5": devolver_venta, "6": crear_usuario}
    while True:
        print("\n--- Retos de ampliación ---")
        print("1. Ventas por rango de fechas\n2. Utilidad estimada\n3. Exportar inventario CSV")
        print("4. Configurar costo unitario (administrador)\n5. Devolver venta (administrador)")
        print("6. Crear usuario (administrador)\n0. Volver")
        opcion = input("Seleccione una opción: ").strip()
        if opcion == "0":
            return
        if opcion in opciones:
            opciones[opcion](estado)
        elif opcion in administrativas:
            requiere_admin(administrativas[opcion], estado)
        else:
            print("Opción inválida.")



def menu_reportes(estado):
    while True:
        print("\n--- Reportes ---")
        print("1. Reporte de existencias y valor de inventario")
        print("2. Reporte de ventas")
        print("3. Ranking de productos más vendidos")
        print("4. Productos con mayor rotación")
        print("5. Indicadores de lotes")
        print("0. Volver")
        op = input("Seleccione una opción: ").strip()
        if op == "1":
            reporte_inventario(estado)
        elif op == "2":
            reporte_ventas(estado)
        elif op == "3":
            ranking_productos_vendidos(estado)
        elif op == "4":
            reporte_rotacion_productos(estado)
        elif op == "5":
            reporte_lotes(estado)
        elif op == "0":
            break
        else:
            print("Opción inválida.")



def menu_inventario(estado):
    while True:
        print("\n--- Movimientos de inventario ---")
        print("1. Registrar entrada manual")
        print("2. Registrar salida manual")
        print("3. Consultar stock por producto")
        print("4. Listar movimientos")
        print("0. Volver")
        op = input("Seleccione una opción: ").strip()
        if op == "1":
            entrada_manual(estado)
        elif op == "2":
            salida_manual(estado)
        elif op == "3":
            codigo = pedir_texto("Código del producto: ").upper()
            if buscar_producto(estado["productos"], codigo):
                print(f"Stock actual: {calcular_stock(estado['movimientos'], codigo)}")
            else:
                print("No existe un producto con ese código.")
        elif op == "4":
            listar_movimientos(estado)
        elif op == "0":
            break
        else:
            print("Opción inválida.")



def menu_lotes(estado):
    while True:
        print("\n--- Gestión de lotes productivos ---")
        print("1. Registrar lote")
        print("2. Cosechar lote")
        print("3. Cancelar lote")
        print("4. Listar lotes")
        print("0. Volver")
        op = input("Seleccione una opción: ").strip()
        if op == "1":
            registrar_lote(estado)
        elif op == "2":
            cosechar_lote(estado)
        elif op == "3":
            cancelar_lote(estado)
        elif op == "4":
            listar_lotes(estado)
        elif op == "0":
            break
        else:
            print("Opción inválida.")



def menu_productos(estado):
    while True:
        print("\n--- Gestión de productos ---")
        print("1. Registrar producto")
        print("2. Listar / buscar productos")
        print("3. Actualizar producto")
        print("4. Desactivar producto")
        print("0. Volver")
        op = input("Seleccione una opción: ").strip()
        if op == "1":
            requiere_admin(registrar_producto, estado)
        elif op == "2":
            listar_productos(estado)
        elif op == "3":
            requiere_admin(actualizar_producto, estado)
        elif op == "4":
            requiere_admin(desactivar_producto, estado)
        elif op == "0":
            break
        else:
            print("Opción inválida.")



def menu_principal():
    print("\n==================== AGROCONTROL CBA ====================")
    print("1. Gestión de productos")
    print("2. Gestión de lotes productivos")
    print("3. Movimientos de inventario")
    print("4. Registrar venta")
    print("5. Consultar ventas")
    print("6. Alertas de stock")
    print("7. Reportes")
    print("8. Guardar datos")
    print("9. Retos de ampliación y usuarios")
    print("0. Salir")
    return input("Seleccione una opción: ").strip()



OPCIONES_MENU = {
    "1": lambda estado: menu_productos(estado),
    "2": lambda estado: menu_lotes(estado),
    "3": lambda estado: menu_inventario(estado),
    "4": lambda estado: registrar_venta(estado),
    "5": lambda estado: consultar_ventas(estado),
    "6": lambda estado: alertas_stock(estado),
    "7": lambda estado: menu_reportes(estado),
    "9": lambda estado: menu_ampliaciones(estado),
}


def main():
    print("Bienvenido a AgroControl CBA")
    global SESION
    SESION = None
    try:
        SESION = iniciar_sesion()
        if SESION is None:
            print("No se inició sesión.")
            return
        estado = cargar_datos()
    except (EOFError, KeyboardInterrupt):
        print("\nInicio de sesión cancelado.")
        return
    except (ValueError, OSError) as error:
        print(f"No es seguro iniciar: {error}. Revise data/ antes de reintentar.")
        return
    while True:
        anterior = deepcopy(estado)
        try:
            opcion = menu_principal()
            if opcion == "0":
                guardar_datos(estado)
                print("Datos guardados. Hasta luego.")
                break
            elif opcion == "8":
                guardar_datos(estado)
                print("Datos guardados correctamente.")
            elif opcion in OPCIONES_MENU:
                OPCIONES_MENU[opcion](estado)
            else:
                print("Opción inválida, intente de nuevo.")
        except (KeyboardInterrupt, EOFError):
            print("\nOperación interrumpida por el usuario.")
            break
        except OSError as error:
            print(f"No se pudo completar el guardado: {error}. Reinicie para recuperar la operación pendiente.")
            break
        except Exception as error:
            estado = anterior
            print(f"Ocurrió un error inesperado: {error}. La aplicación continúa.")



if __name__ == "__main__":
    main()
