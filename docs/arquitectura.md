# Arquitectura y decisiones de diseño

## 1. Vista general

```
┌────────────────────────── ui/ (Tkinter) ──────────────────────────┐
│  ventana_principal · formulario · cuotero · lista_proformas        │
│  Solo lee/pinta widgets, valida con validadores.py y delega.       │
└───────────────┬───────────────────────┬────────────────────────────┘
                │                       │
        ┌───────▼───────┐       ┌───────▼───────┐       ┌────────────┐
        │  calculo.py   │       │     db.py     │       │   pdf.py   │
        │  fechas.py    │       │ sqlite3 (?)   │       │ reportlab  │
        │  (puro)       │       │ repositorio   │       │            │
        └───────────────┘       └───────────────┘       └────────────┘
        validadores.py · formato.py · config.py (variables de entorno)
```

Flujo de "Guardar": `UI → validadores (¿datos válidos?) → calculo (resultado) → db.insertar → UI (mensaje)`.

## 2. Módulos

| Módulo | Responsabilidad | Depende de |
|---|---|---|
| `config.py` | Lee `.env`/variables de entorno con valores por defecto seguros | stdlib |
| `fechas.py` | Día hábil, suma de meses, días entre fechas | stdlib |
| `calculo.py` | `ParametrosProforma` → `ResultadoProforma` (cuotero, totales, TAE) | `fechas` |
| `validadores.py` | Validar y normalizar texto de entrada; lanza `ErrorValidacion` | stdlib |
| `formato.py` | `Gs. 1.234.567`, fechas `DD/MM/AAAA`, documento con puntos | stdlib |
| `db.py` | Crear esquema, CRUD, N° de operación, respaldo | `sqlite3` |
| `pdf.py` | Dibujar el PDF del cuotero | `reportlab` |
| `ui/*` | Ventanas y widgets | `tkinter`, todo lo anterior |

Estructuras de datos: `dataclass(frozen=True)` para `ParametrosProforma`, `FilaCuota`, `ResultadoProforma`
y `Proforma` (registro guardado).

## 3. ¿Por qué Tkinter? (criterio de diseño — indicador 16)

| Opción | Evaluación para este problema |
|---|---|
| **Tkinter** ✅ | App **local** de un solo usuario, sin servidor ni internet, instalación = Python. Incluido en la biblioteca estándar; los formularios y tablas (`ttk.Treeview`) cubren la necesidad. |
| Django | Pensado para aplicaciones web multiusuario con servidor y navegador. Aquí sería sobredimensionado: hay que desplegar un servidor, manejar sesiones y CSRF para un uso individual. |
| pandas/numpy | Orientado a análisis de datos, no a una interfaz de captura/consulta. Se podría usar para el cálculo, pero la fórmula es corta y aritmética exacta con `Decimal` es más adecuada para dinero. |

Además, el prototipo original ya era una "aplicación de una sola máquina" con SQLite local: Tkinter +
`sqlite3` es la traducción más directa.

## 4. ¿Por qué SQLite y reportlab?

- **SQLite**: un solo archivo, sin instalar servidor, transaccional, incluido en Python. Suficiente
  para miles de proformas.
- **reportlab**: librería estándar de facto para PDF en Python; control fino de tablas, colores y
  paginación (equivalente a jsPDF + AutoTable del prototipo).

## 5. Manejo de errores

- Dominio: `ErrorValidacion(campo, mensaje)` para entradas inválidas.
- Persistencia: `ErrorBaseDatos` envuelve `sqlite3.Error`.
- UI: un único *decorador/contexto* captura `ErrorValidacion` (mensaje junto al campo) y cualquier
  otra `Exception` (log + mensaje genérico). `Tk.report_callback_exception` está sobreescrito para que
  ningún error interno cierre la ventana ni muestre un traceback.

## 6. Pruebas

`pytest` cubre: cálculo (caso de oro, n=1, tasa 0, fin de semana, 1er vto modificado, cierre de saldo
en 0), validadores (letras, `000000`, vacíos, rangos), BD (CRUD, N° de operación diario, SQL injection
como dato) y PDF (se genera y no está vacío). La UI se prueba manualmente con la lista de §Defensa.
