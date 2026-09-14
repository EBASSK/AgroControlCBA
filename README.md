# AgroControl CBA

Sistema de gestión agrícola y de inventario desarrollado en Python para controlar productos, stock, lotes, ventas y reportes operativos de una empresa agropecuaria o productora.

## Descripción

AgroControl CBA permite llevar el control de:

- Productos y categorías
- Lotes productivos con fechas de siembra y cosecha
- Entradas y salidas de inventario
- Ventas y devoluciones
- Alertas de stock mínimo
- Reportes de inventario, ventas y rotación
- Usuarios con roles de acceso
- Backups automáticos de la información

La aplicación funciona desde consola y guarda los datos en archivos JSON dentro de la carpeta `data/`.

## Funcionalidades principales

### Gestión de productos
- Registro de productos con código, nombre, categoría, unidad, precio y stock mínimo
- Búsqueda y listado de productos
- Actualización de datos
- Desactivación de productos sin perder su historial

### Gestión de lotes
- Registro de lotes asociados a un producto
- Seguimiento de estado: EN_PRODUCCION, COSECHADO, CANCELADO
- Cosecha con generación automática de entrada de inventario
- Consulta de lotes activos y su producción

### Inventario
- Entradas manuales de stock
- Salidas manuales de stock
- Control del stock disponible por producto
- Validación de stock insuficiente antes de registrar salidas o ventas

### Ventas
- Registro de ventas con múltiples productos
- Cálculo automático del total
- Validación de stock disponible por ítem
- Consulta de ventas por fecha
- Devolución de ventas con reintegración del inventario

### Reportes y alertas
- Inventario actual y valor estimado
- Ventas acumuladas
- Ranking de productos más vendidos
- Rotación de productos
- Indicadores de lotes
- Alertas por stock mínimo
- Exportación del inventario a CSV

### Seguridad y usuarios
- Inicio de sesión con usuario y contraseña
- Cifrado de contraseñas con PBKDF2-HMAC-SHA256
- Roles:
  - OPERADOR
  - INSTRUCTOR/ADMINISTRADOR
- Acciones administrativas con restricción por rol

## Requisitos

- Python 3.10 o superior
- Sistema operativo compatible con Python

No se requieren dependencias adicionales, ya que la aplicación usa solo la biblioteca estándar de Python.

## Instalación

1. Clona o descarga este repositorio.
2. Abre una terminal dentro de la carpeta del proyecto.
3. Asegúrate de tener Python instalado y disponible en el PATH.
4. Ejecuta la aplicación:

```bash
python main.py
```

## Primer uso

La primera vez que ejecutes la aplicación, se solicitará crear un usuario administrador.

Debe ingresar:
- usuario
- contraseña (mínimo 8 caracteres)
- confirmación de contraseña

A partir de ese momento, podrás iniciar sesión con ese usuario y acceder al menú principal.

## Menú principal

La aplicación ofrece estas opciones principales:

1. Gestión de productos
2. Gestión de lotes productivos
3. Movimientos de inventario
4. Registrar venta
5. Consultar ventas
6. Alertas de stock
7. Reportes
8. Guardar datos
9. Retos de ampliación y usuarios
0. Salir

## Estructura del proyecto

```text
AgroControlCBA/
├── main.py
├── README.md
├── data/
│   ├── productos.json
│   ├── lotes.json
│   ├── movimientos.json
│   ├── ventas.json
│   ├── usuarios.json
│   ├── transaccion.json
│   └── backups/
│       └── ...
└── .gitignore (si aplica)
```

### Carpetas importantes

- `main.py`: lógica principal de la aplicación
- `data/`: almacenamiento de los datos del sistema
- `data/backups/`: copias de seguridad automáticas antes de guardar cambios

## Datos y almacenamiento

La aplicación guarda la información en archivos JSON para facilitar el manejo y la restauración de datos.

Cada vez que se realiza un guardado, se genera un respaldo automático en `data/backups/` antes de reemplazar los archivos principales.

## Consideraciones

- Se recomienda no editar los archivos JSON manualmente mientras la aplicación esté en uso.
- Si ocurre un problema con los datos, puedes revisar la carpeta `backups/` para recuperar versiones anteriores.
- La aplicación está pensada para uso en consola y para entornos de operación pequeños y medianos.

## Licencia

Este proyecto se entrega como herramienta de gestión interna sin una licencia específica definida en el repositorio.

## Autor
Sebastián Cáceres Osuan

Correo: sebas25caceres@gmail.com