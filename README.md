# Sistema de Proformas — Fundación Industrial

Aplicación de escritorio para que un **asesor comercial** calcule, en el momento y frente al cliente, la
cuota mensual de un préstamo. Calcula con el **Método Francés** (cuota fija) incluyendo **gastos
administrativos, IVA y seguro nivelado**, guarda cada proforma en una base de datos **SQLite** y emite el
**cuotero en PDF** para entregar.

Está hecha 100 % con el ecosistema Python: **Tkinter** (interfaz), **sqlite3** (base de datos),
**reportlab** (PDF) y **pytest** (pruebas). No necesita internet ni instalar ningún servidor.

> Proyecto final del curso de Python. Es la migración a Python del prototipo web
> `Cálculo Proforma Asesor Comercial.html`, que se usó como referencia de las reglas de negocio.

---

## Contenido

1. [Qué hace](#qué-hace)
2. [Requisitos e instalación](#requisitos-e-instalación)
3. [Cómo ejecutarla](#cómo-ejecutarla)
4. [Guía de uso](#guía-de-uso)
5. [Cómo se calcula](#cómo-se-calcula)
6. [Validaciones](#validaciones)
7. [Estructura del proyecto](#estructura-del-proyecto)
8. [Base de datos](#base-de-datos)
9. [Configuración](#configuración)
10. [Pruebas](#pruebas)
11. [Seguridad](#seguridad)
12. [Solución de problemas](#solución-de-problemas)
13. [Límites conocidos](#límites-conocidos)
14. [Documentación adicional](#documentación-adicional)

---

## Qué hace

| Función | Descripción |
|---|---|
| **Cálculo en vivo** | Al cambiar cualquier parámetro se recalculan al instante la cuota, el seguro, el total a pagar, la T.A.E. y el cuotero completo. |
| **Cuotero** | Tabla de amortización cuota por cuota, en vista *comercial* (cliente) o *analítica* (columnas de la planilla Excel). |
| **Guardar / editar / eliminar** | CRUD completo sobre SQLite. Cada proforma recibe un N° de operación `AAAAMMDD` + secuencia diaria (`20261124001`). |
| **Búsqueda** | Por cliente, documento, teléfono o N° de operación. |
| **PDF** | Reporte A4 con logo, datos del solicitante, 4 indicadores clave y el cuotero (varias páginas si hace falta). |
| **Calendario** | Las fechas se escriben o se eligen con el botón 📅. |
| **Respaldar / Importar BD** | Copia la base de datos y la carga en otra máquina (combinando o reemplazando). |
| **Validación estricta** | Rechaza letras en campos numéricos, teléfonos falsos, campos vacíos, fechas imposibles, etc. |

## Requisitos e instalación

- **Windows 10/11** (el código es portable, pero se probó en Windows).
- **Python 3.11 o superior** con Tkinter (viene incluido en el instalador oficial de python.org; al
  instalar, dejar marcada la opción *tcl/tk and IDLE*).

```powershell
# 1. Entrar a la carpeta del proyecto
cd SistemaProforma

# 2. (Recomendado) entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. (Opcional) configuración personalizada
copy .env.example .env
```

Dependencias externas: solo `reportlab` (PDF) y `pytest` (pruebas). Todo lo demás es biblioteca estándar.

## Cómo ejecutarla

```powershell
python main.py
```

Equivalente: `python -m proformas` (con `PYTHONPATH=src`). La primera vez se crea
`data/proformas.db`; los PDF se guardan en `data/pdf/`.

## Guía de uso

La ventana tiene cuatro secciones numeradas:

1. **Datos del cliente** — nombre, documento (C.I., RUC o pasaporte), teléfono y observaciones
   (opcional). Los campos con `*` son obligatorios.
2. **Parámetros** — fecha de desembolso, primer vencimiento, capital, cuotas, IVA, T.A.N., gastos
   administrativos, seguro y criterio de redondeo. Hay atajos para sumar capital (+1M, +5M, +10M), elegir
   plazo (6/12/18/24/36 meses) y seguro (micro 0,25 %, funcionario 0,12 %, sin seguro).
3. **Vista previa del cuotero** — se actualiza sola con cada cambio. Las tarjetas superiores muestran
   cuota final, cuota base + gastos, seguro nivelado y total a pagar.
4. **Proformas guardadas** — historial con buscador y botones *Editar*, *Descargar PDF* y *Eliminar*.

**Flujo típico**

1. Ingresar los datos del cliente y ajustar capital y plazo.
2. **Guardar Proforma** → aparece en la lista con su N° de operación.
3. **Generar PDF** → se crea y se abre para imprimir o enviar.
4. Para corregir algo: seleccionar la proforma → **Editar** (doble clic también) → modificar →
   **Actualizar Proforma**.

**Fechas.** Si el primer vencimiento cae en sábado o domingo, la app lo traslada al lunes sin cobrar
interés por esos días y lo avisa en la barra de estado.

**Llevar los datos a otra máquina**

1. En la máquina de origen: **Respaldar BD…** y guardar el archivo `.db`.
2. Copiar el archivo a la otra máquina (pendrive, correo, etc.).
3. En la otra máquina: **Importar BD…** → elegir el archivo y el modo:
   - **Combinar**: agrega las proformas que no existen, sin borrar las actuales ni duplicar.
   - **Reemplazar**: deja solo las del respaldo. Pide confirmación y antes guarda una copia
     automática en `data/backups/`.

## Cómo se calcula

Resumen (detalle y fórmulas en [`docs/reglas-negocio.md`](docs/reglas-negocio.md)):

- **Tasa mensual** = T.A.N. / 12; con IVA = tasa mensual × (1 + IVA).
- **Cuota base** (Método Francés): `capital · i·(1+i)ⁿ / ((1+i)ⁿ − 1)`, con `i` la tasa mensual con IVA.
- **Gastos administrativos** = % del capital + IVA, repartidos en partes iguales entre las cuotas.
- **Seguro nivelado**: el seguro real baja con el saldo; se promedia (con IVA) para que todas las cuotas
  sean iguales.
- **Cuota final** = cuota base + gastos mensuales + seguro nivelado (+ recargo si el primer período
  supera los 30 días).
- **T.A.E.**: tasa anual efectiva que iguala lo recibido con lo pagado (cuotas en sus fechas reales,
  act/365), resuelta por bisección.
- **Redondeo**: *institucional* (guaraníes enteros, mitad hacia arriba como `Math.round` de JavaScript) o
  *exacto* (2 decimales).

**Verificación.** El cálculo en Python se comparó con el prototipo HTML en 8 escenarios (incluyendo
primer vencimiento modificado, una sola cuota, tasa 0 %, 120 cuotas y modo exacto): cada cuota del
cuotero coincide (`tests/golden/referencia_html.json`). Caso de referencia: capital 10.000.000, 12 cuotas,
T.A.N. 24 %, IVA 10 %, gastos 2 %, seguro 0,25 % → **cuota final Gs. 991.072**, total Gs. 11.892.864,
T.A.E. 38,88 %.

## Validaciones

| Campo | Regla |
|---|---|
| Campos numéricos | Solo dígitos (y un separador decimal donde corresponde): las letras y símbolos no se pueden escribir y se vuelven a validar al guardar. |
| Nombre | Obligatorio, 3–120 caracteres, solo letras, números y signos comunes. |
| Documento | C.I./RUC (`4.567.890`, `4.567.890-1`) o pasaporte alfanumérico (6–12). |
| Teléfono | Dígitos, espacios, `+ - ( )`; 6–15 dígitos; rechaza `000000` y similares. |
| Capital | Entero > 0 y ≤ 100.000.000.000 (acepta puntos de miles). |
| Cuotas | Entero entre 1 y 120. |
| IVA / gastos / seguro / T.A.N. | Decimal ≥ 0 dentro de rango (IVA ≤ 50, gastos ≤ 50, seguro ≤ 10, T.A.N. ≤ 200). |
| Fechas | `DD/MM/AAAA` real (rechaza 31/02), años 2000–2100; el 1er vencimiento no puede ser anterior al desembolso. |
| Observaciones | Opcional, hasta 300 caracteres. |

Cada error se muestra en rojo bajo su campo, con un texto que dice cómo corregirlo. Ninguna entrada
inesperada cierra la aplicación ni muestra un error técnico.

## Estructura del proyecto

```
SistemaProforma/
├── main.py                    # atajo para ejecutar: python main.py
├── requirements.txt           # reportlab, pytest
├── pyproject.toml             # configuración de pytest
├── .env.example               # variables de entorno de ejemplo
├── AGENTS.md                  # instrucciones para agentes de IA
├── src/proformas/
│   ├── __main__.py            # punto de entrada (log + BD + ventana)
│   ├── config.py              # lectura de variables de entorno
│   ├── calculo.py             # lógica financiera PURA (Método Francés, seguro, TAE)
│   ├── fechas.py              # días hábiles y suma de meses
│   ├── validadores.py         # validación de entradas (lista blanca)
│   ├── formato.py             # formato de montos, fechas y documentos
│   ├── db.py                  # SQLite: CRUD, respaldo e importación
│   ├── pdf.py                 # generación del PDF con reportlab
│   └── ui/
│       ├── app.py             # ventana principal (orquesta: leer → validar → calcular → guardar)
│       └── widgets.py         # campos con filtro de teclado, calendario y estilos
├── tests/                     # pytest (122 pruebas) + valores de referencia del prototipo HTML
├── docs/                      # especificación, arquitectura, reglas, seguridad, defensa
└── data/                      # base de datos, PDF y backups (ignorados por git)
```

**Capas.** `calculo`, `fechas`, `validadores` y `formato` son funciones puras (sin Tkinter, SQLite ni
reportlab), por eso se prueban fácilmente. La interfaz solo orquesta; la persistencia y el PDF viven en
módulos propios.

```
        ui/ (Tkinter) ──► validadores ──► calculo ──► db (SQLite)
              │                              │
              └────────────► pdf (reportlab) ◄┘
```

## Base de datos

Un único archivo SQLite (`data/proformas.db`) con la tabla `proformas`: datos del cliente, parámetros
del cálculo (capital, tasa, cuotas, IVA, gastos, seguro, redondeo, fechas) y los resultados (cuota base,
seguro, cuota final, total a pagar). El cuotero **no** se guarda: se recalcula a partir de los
parámetros, así siempre es consistente con las reglas vigentes. Las restricciones `CHECK` de la tabla
son una segunda barrera de validación. Detalle del esquema en [`docs/spec.md`](docs/spec.md).

## Configuración

La app funciona sin configurar nada. Para personalizar, copiar `.env.example` a `.env`
(no se versiona) o definir variables de entorno:

| Variable | Defecto | Uso |
|---|---|---|
| `PROFORMAS_DB_PATH` | `data/proformas.db` | Ruta de la base de datos |
| `PROFORMAS_PDF_DIR` | `data/pdf` | Carpeta de los PDF |
| `PROFORMAS_LOG_PATH` | `data/app.log` | Archivo de log (errores técnicos) |
| `PROFORMAS_EMPRESA` | `FUNDACIÓN INDUSTRIAL` | Nombre en el pie del PDF |
| `PROFORMAS_RUC` | `80011774-3` | RUC en el encabezado del PDF |
| `PROFORMAS_DIRECCION` | `Senador Long N°625 c/ Lillo` | Dirección en el PDF |
| `PROFORMAS_TELEFONO` | `(021) 605 700` | Teléfono en el PDF |

## Pruebas

```powershell
python -m pytest          # las 122 pruebas
python -m pytest -v       # con detalle
```

| Archivo | Qué comprueba |
|---|---|
| `test_calculo.py` | El cálculo coincide con el prototipo HTML (8 escenarios, cada cuota), el saldo cierra en 0 y las cuotas son iguales. |
| `test_validadores.py` | Letras, símbolos, `000000`, vacíos, rangos, fechas imposibles, texto hostil. |
| `test_db.py` | CRUD, N° de operación diario, búsqueda con comodines, restricciones y SQL injection tratado como dato. |
| `test_importar.py` | Importación: combinar, reemplazar, duplicados, archivo ajeno o dañado, filas inválidas. |
| `test_pdf.py` | El PDF se genera y los nombres de archivo se sanean. |
| `test_ui_humo.py`, `test_ui_calendario_importar.py` | La ventana real: flujo completo, errores de campo, calendario e importación. |

## Seguridad

- Configuración en **variables de entorno** (`.env` no se versiona).
- **SQL parametrizado** en todas las consultas.
- **Validación por lista blanca** en el teclado, al guardar y al importar.
- **Sin errores técnicos al usuario**: se guardan en `data/app.log` y se muestra un mensaje comprensible.
- **Sin red**: la app no hace conexiones.
- **Nombres de PDF saneados** (solo `A-Z0-9_`) contra path traversal.
- **Importación segura**: archivo en solo lectura, verificación de formato e integridad, transacción atómica
  y copia previa al reemplazar.
- **Datos personales mínimos**: la base de datos y los PDF no se suben a git.

Detalle y cómo se verifica cada punto: [`docs/seguridad.md`](docs/seguridad.md).

## Solución de problemas

| Problema | Causa / solución |
|---|---|
| `ModuleNotFoundError: No module named 'tkinter'` | Reinstalar Python marcando *tcl/tk and IDLE*. |
| `ModuleNotFoundError: No module named 'reportlab'` | Ejecutar `pip install -r requirements.txt` (con el entorno virtual activado). |
| "No se pudo generar el PDF" | El archivo está abierto en otro programa: cerrarlo y reintentar. |
| "El archivo seleccionado no es una base de datos de proformas válida" | Solo se pueden importar respaldos hechos con **Respaldar BD…** de esta aplicación (no la exportación del prototipo web). |
| Algo falló sin explicación | Ver `data/app.log`: ahí queda el detalle técnico. |

## Límites conocidos

- Un solo usuario por máquina, sin inicio de sesión.
- La base de datos no está cifrada (se asume una PC de oficina con acceso controlado).
- Solo guaraníes; sin integración con sistemas contables.
- El cálculo replica el prototipo y debería validarse con el área financiera antes de uso productivo.

## Documentación adicional

| Documento | Contenido |
|---|---|
| [AGENTS.md](AGENTS.md) | Instrucciones y reglas para agentes de IA (stack, estructura, seguridad, validación) |
| [docs/spec.md](docs/spec.md) | Especificación: qué hace, qué datos maneja, qué funciones incluye |
| [docs/arquitectura.md](docs/arquitectura.md) | Capas, módulos y por qué Tkinter |
| [docs/reglas-negocio.md](docs/reglas-negocio.md) | Fórmulas del cálculo |
| [docs/seguridad.md](docs/seguridad.md) | Patrones de seguridad y su verificación |
| [docs/uso-de-ia.md](docs/uso-de-ia.md) | Bitácora de uso de IA y reflexión |
| [docs/rubrica.md](docs/rubrica.md) | Rúbrica de defensa mapeada a evidencias |
| [docs/guia-defensa.md](docs/guia-defensa.md) | Guion de 10 minutos y checklist |
