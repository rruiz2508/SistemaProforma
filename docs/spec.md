# Especificación (spec.md) — Sistema de Proformas

Versión 1.0 · Proyecto final del curso de Python · Defensa: 24/11/2026

## 1. Problema y público

Un **asesor comercial** de una financiera (Fundación Industrial) necesita decirle a un cliente, en el
momento, cuánto pagaría por mes si pide un préstamo. Hoy lo hace con planillas o a mano: es lento,
propenso a errores (redondeos, IVA, seguro, fechas de fin de semana) y no deja registro.

**Solución:** una aplicación de escritorio que calcula la proforma al instante, la guarda en una base
de datos local y emite un **PDF (cuotero)** para entregar al cliente.

**Usuario:** asesor comercial, sin conocimientos técnicos. Trabaja en una PC Windows, sin internet.

## 2. Alcance

**Incluye**
- Cálculo de proforma con Método Francés + gastos administrativos + IVA + seguro nivelado.
- CRUD de proformas (crear, listar/buscar, editar, eliminar) en SQLite.
- Generación de PDF del cuotero (de la proforma en pantalla o de una guardada).
- Validación estricta de entradas.

**No incluye (fuera de alcance)**: usuarios/login, red o nube, envío por correo, múltiples monedas,
firma electrónica, integración con sistemas contables.

## 3. Datos que maneja

### 3.1 Entidad `proformas` (tabla SQLite)

| Columna | Tipo | Notas |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `nro_operacion` | TEXT UNIQUE | `AAAAMMDD` + secuencia diaria de 3 dígitos (`20261124001`) |
| `fecha_creacion` | TEXT | ISO `AAAA-MM-DD HH:MM` |
| `fecha_actualizacion` | TEXT | |
| `nombre_cliente` | TEXT NOT NULL | |
| `documento` | TEXT NOT NULL | C.I., RUC o pasaporte |
| `telefono` | TEXT NOT NULL | |
| `observaciones` | TEXT | opcional |
| `fecha_desembolso` | TEXT NOT NULL | ISO |
| `primer_vencimiento` | TEXT NOT NULL | ISO (ya trasladado a día hábil) |
| `primer_vto_nominal` | TEXT | ISO original si hubo traslado por fin de semana |
| `capital` | INTEGER NOT NULL | Gs. |
| `tasa_anual` | REAL NOT NULL | TAN % |
| `cuotas` | INTEGER NOT NULL | 1–120 |
| `iva_pct` | REAL NOT NULL | |
| `pct_gastos` | REAL NOT NULL | |
| `tasa_seguro` | REAL NOT NULL | % mensual |
| `redondeo_entero` | INTEGER NOT NULL | 1 = institucional, 0 = exacto |
| `cuota_base_gastos` | REAL NOT NULL | resultado |
| `seguro_mensual` | REAL NOT NULL | resultado |
| `cuota_final` | REAL NOT NULL | resultado |
| `total_pagar` | REAL NOT NULL | resultado |

Restricciones `CHECK` en BD (capital > 0, cuotas 1–120, porcentajes ≥ 0) como segunda barrera.

### 3.2 Parámetros de cálculo (entradas)

| Parámetro | Defecto | Rango |
|---|---|---|
| Fecha de desembolso | hoy | fecha válida |
| Primer vencimiento | desembolso + 1 mes (hábil) | ≥ desembolso |
| Capital solicitado (Gs.) | 10.000.000 | 1 – 100.000.000.000 |
| Cuotas mensuales (n) | 12 | 1 – 120 |
| Tasa de IVA (%) | 10 | 0 – 50 |
| TAN (%) | 24 | 0 – 200 |
| Gastos administrativos (%) | 2 | 0 – 50 |
| Seguro (% mensual) | 0,25 | 0 – 10 |
| Redondeo | Institucional (entero) | entero / exacto |

## 4. Funciones

| ID | Función | Descripción |
|---|---|---|
| F1 | Calcular proforma | Recalcula en vivo al cambiar cualquier parámetro. Muestra 4 indicadores (cuota final, base + gastos, seguro nivelado, total a pagar), TAE y tasas con IVA. |
| F2 | Ver cuotero | Tabla de amortización: N°, vencimiento, días, saldo inicial, amortización, gastos, interés, IVA, seguro, cuota final, saldo final y totales. Dos vistas: *Comercial* y *Analítica*. |
| F3 | Guardar proforma | Valida datos del cliente y parámetros; inserta en SQLite; asigna N° de operación. |
| F4 | Listar y buscar | Tabla de proformas guardadas con búsqueda por cliente, documento, teléfono o N° de operación. |
| F5 | Editar proforma | Carga una proforma guardada en el formulario; "Actualizar" modifica el registro. |
| F6 | Eliminar proforma | Con diálogo de confirmación. |
| F7 | Generar PDF | PDF A4 con datos del cliente, resumen y cuotero completo, a `data/pdf/`. Se abre al terminar. |
| F8 | Nueva / limpiar | Restablece el formulario a valores por defecto. |
| F9 | Respaldo de BD | Copia el archivo `.db` a una ubicación elegida por el usuario. |

## 5. Pantalla principal (Tkinter)

Una ventana con:
1. **Datos del cliente** (nombre, documento, teléfono, observaciones).
2. **Parámetros** (los de §3.2) con indicadores TAE/mensual en vivo.
3. **Resumen**: 4 tarjetas con los totales.
4. **Cuotero** (`ttk.Treeview`) con selector de vista.
5. **Proformas guardadas** (`ttk.Treeview`) con buscador y botones Editar / PDF / Eliminar.
6. Barra de estado para mensajes (éxito/error).

Los campos numéricos rechazan caracteres inválidos mientras se escribe (`validatecommand`) y los
errores de campo se muestran junto al campo en rojo, con un texto que explica qué corregir.

## 6. Criterios de aceptación

1. `python -m proformas` abre la ventana sin errores en una instalación limpia (tras `pip install -r requirements.txt`).
2. Caso de oro (AGENTS.md §8) reproduce los valores del prototipo HTML (tolerancia ±1 Gs.).
3. Crear → aparece en la lista; Editar → cambios visibles; Eliminar (confirmando) → desaparece.
4. El PDF se genera, abre y su total coincide con el de pantalla.
5. Letras en campos numéricos, `000000` o vacío en teléfono, campos obligatorios vacíos, capital
   negativo/cero, fecha inválida: todos producen un mensaje claro y **no** cierran la app.
6. `python -m pytest` pasa completo.

## 7. Requisitos no funcionales

- **Seguridad**: ver `docs/seguridad.md`.
- **Rendimiento**: recálculo < 100 ms para n = 120.
- **Portabilidad**: Windows 10/11, Python 3.11+. Sin servicios externos.
- **Mantenibilidad**: lógica de negocio separada de la UI, con pruebas automatizadas.
