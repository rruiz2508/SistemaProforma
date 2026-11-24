# AGENTS.md — Instrucciones para agentes de IA

> Este archivo guía a cualquier agente de IA (Claude Code, Copilot, etc.) que trabaje en este repositorio.
> Léelo completo antes de escribir código. La fuente de verdad funcional es [`docs/spec.md`](docs/spec.md).

## 1. Qué es este proyecto

**Sistema de Proformas** — aplicación de escritorio (Tkinter) para que un asesor comercial de
*Fundación Industrial* calcule proformas de préstamos con **Método Francés**, gastos administrativos,
IVA y seguro nivelado; las guarde en **SQLite** y genere el **reporte PDF** (cuotero).

Es la migración a Python de un prototipo web (`Cálculo Proforma Asesor Comercial.html`), que es la
**referencia de las reglas de negocio** (la lógica está en su `<script>`, función `calculateProforma`).

Es un proyecto final de curso de Python: se evalúa con `docs/rubrica.md`. Priorizamos código claro,
validación robusta y que sea fácil de explicar en 10 minutos.

## 2. Stack (solo ecosistema Python)

| Necesidad | Herramienta |
|---|---|
| Lenguaje | Python 3.11+ (probado en 3.14) |
| Interfaz | `tkinter` + `tkinter.ttk` (biblioteca estándar) |
| Base de datos | `sqlite3` (biblioteca estándar) |
| PDF | `reportlab` |
| Pruebas | `pytest` |

**No agregar** dependencias fuera de `requirements.txt` sin justificarlo. **No** usar Node, JS, web
frameworks ni ORMs: el alcance es una app de escritorio simple.

## 3. Estructura

```
SistemaProforma/
├── AGENTS.md              # este archivo
├── README.md              # cómo instalar y ejecutar
├── requirements.txt
├── .env.example           # variables de entorno (copiar a .env)
├── docs/
│   ├── spec.md            # especificación funcional (qué hace, qué datos, qué funciones)
│   ├── arquitectura.md    # capas, módulos y decisiones (por qué Tkinter)
│   ├── reglas-negocio.md  # fórmulas del cálculo (Método Francés, seguro, TAE, fechas)
│   ├── seguridad.md       # patrones de seguridad y cómo se verifican
│   ├── uso-de-ia.md       # bitácora de uso de IA y reflexión
│   ├── rubrica.md         # rúbrica de defensa mapeada a evidencias
│   └── guia-defensa.md    # guion de 10 minutos
├── src/proformas/
│   ├── __main__.py        # punto de entrada: python -m proformas
│   ├── config.py          # lee variables de entorno
│   ├── calculo.py         # lógica financiera PURA (sin UI, sin BD)
│   ├── fechas.py          # fechas hábiles y sumas de meses
│   ├── validadores.py     # validación/normalización de entradas PURA
│   ├── formato.py         # formato de montos (Gs. 1.234.567) y fechas
│   ├── db.py              # acceso a SQLite (consultas parametrizadas)
│   ├── pdf.py             # generación del PDF con reportlab
│   └── ui/                # app.py (ventana principal) y widgets.py (campos con filtro de teclado)
├── main.py                # atajo: python main.py
├── pyproject.toml         # configuración de pytest (pythonpath=src)
├── tests/                 # pytest (incluye golden/ con valores del prototipo HTML)
└── data/                  # BD y PDF generados (ignorados por git)
```

## 4. Comandos

```powershell
python -m venv .venv ; .\.venv\Scripts\Activate.ps1   # entorno virtual
pip install -r requirements.txt                       # dependencias
python -m pytest                                      # pruebas
python main.py                                        # ejecutar la aplicación
```

## 5. Reglas de arquitectura

1. **Separación de capas.** `calculo.py`, `fechas.py`, `validadores.py`, `formato.py` son funciones puras:
   no importan `tkinter`, `sqlite3` ni `reportlab`. La UI solo orquesta: lee campos → valida →
   llama al cálculo → muestra/guarda.
2. **Dinero.** Los montos en guaraníes (Gs.) son enteros en modo "Redondeo institucional" (redondeo
   half-up como `Math.round` de JS, función `redondeo_js`; **no** `round()` de Python, que es half-even).
   En modo "exacto" se redondea a 2 decimales. El cálculo replica el prototipo con `float`; las pruebas
   comparan con tolerancia (`pytest.approx`), nunca con `==` entre floats calculados.
3. **Una sola fuente de reglas.** Las fórmulas viven en `calculo.py` y están descritas en
   `docs/reglas-negocio.md`. Si cambia una regla, se cambia en ambos y se agrega/actualiza un test.
4. **Fechas.** Vencimientos en sábado/domingo se trasladan al lunes (sin recargo de interés).
5. **Tipado y docstrings** en funciones públicas. Nombres de dominio en español (`capital`,
   `cuota_final`); nombres técnicos genéricos en inglés solo si son estándar.
6. **Un cambio = un propósito.** Commits pequeños y descriptivos (en español, imperativo).

## 6. Reglas de seguridad (obligatorias)

Detalle y verificación en [`docs/seguridad.md`](docs/seguridad.md).

- **Secretos/configuración en variables de entorno** (`.env`, nunca versionado). No hardcodear rutas
  absolutas, claves ni datos institucionales sensibles en el código.
- **SQL siempre parametrizado** (`?`). Prohibido construir SQL con f-strings o `+` con datos del usuario.
- **Validar toda entrada** antes de calcular o guardar (ver §7). Rechazar, no "arreglar en silencio".
- **No mostrar errores técnicos al usuario.** Capturar excepciones en la frontera de la UI, registrar
  el detalle en un log local (`logging`) y mostrar un mensaje comprensible con `messagebox`.
- **Datos personales mínimos.** Solo nombre, documento, teléfono y observaciones del cliente. No
  imprimir datos de clientes en logs ni en la consola.
- **Permisos mínimos.** La app solo escribe en `data/`. El nombre de archivo del PDF se sanea
  (`[A-Z0-9_]`) para evitar rutas maliciosas (path traversal).
- **Eliminación con confirmación** explícita del usuario.

## 7. Reglas de validación (evaluadas en la defensa)

| Campo | Regla |
|---|---|
| Campos numéricos (capital, plazo, tasas) | Solo dígitos (y un separador decimal donde aplique). Rechazar letras y símbolos *al escribir* y *al guardar*. |
| Teléfono | Solo dígitos, espacios, `+`, `-`, `( )`. Entre 6 y 15 dígitos. Rechazar todos los dígitos iguales (`000000`, `111111`). |
| Obligatorios (nombre, documento, teléfono) | No vacíos tras `strip()`. Mensaje claro por campo. |
| Documento | C.I./RUC (`4.567.890` o `4.567.890-1`) o pasaporte alfanumérico (6–12 caracteres). |
| Capital | Entero > 0 y ≤ tope razonable (p. ej. 100.000.000.000). |
| Cuotas | Entero 1–120. |
| TAN, IVA, gastos, seguro | Decimal ≥ 0 dentro de rangos (ver `docs/spec.md`). |
| Fechas | Formato `DD/MM/AAAA` válido; 1er vencimiento ≥ desembolso. |
| Observaciones | Opcional, máx. 300 caracteres. |

Cualquier entrada inesperada debe terminar en un **mensaje comprensible**, nunca en un traceback ni en
el cierre de la app.

## 8. Pruebas

- Toda función de `calculo.py`, `fechas.py`, `validadores.py` y `db.py` tiene pruebas en `tests/`.
- Caso de oro (generado ejecutando el prototipo HTML): capital 10.000.000, 12 cuotas, TAN 24 %, IVA 10 %,
  gastos 2 %, seguro 0,25 %, redondeo entero → **cuota final Gs. 991.072**, seguro nivelado Gs. 15.489,
  total a pagar Gs. 11.892.864, TAE 38,88 %. Hay 8 escenarios en `tests/golden/referencia_html.json`.
- La BD en pruebas usa `:memory:` o un archivo temporal (`tmp_path`), nunca `data/`.
- Antes de dar una tarea por terminada: `python -m pytest` en verde.

## 9. Qué NO hacer

- No reescribir ni borrar el HTML de referencia ni el PDF de la rúbrica.
- No agregar login, red, nube, ni envío de datos a servicios externos (fuera de alcance).
- No inventar reglas de negocio: si algo es ambiguo, consultar `docs/reglas-negocio.md` y el HTML;
  si sigue ambiguo, **preguntar** al usuario.
- No dejar `print()` de depuración ni `except:` desnudos.
- No commitear `.env`, bases de datos ni PDF generados.

## 10. Flujo de trabajo esperado del agente

1. Leer `docs/spec.md` y este archivo.
2. Proponer un plan corto antes de cambios grandes.
3. Implementar en pasos pequeños, con tests.
4. Ejecutar `python -m pytest` y reportar el resultado real (incluidos fallos).
5. Registrar en `docs/uso-de-ia.md` qué se generó con IA y qué hubo que corregir.
