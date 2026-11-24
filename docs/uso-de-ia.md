# Uso de IA en el proyecto (indicadores 18, 19 y 20)

> Completar las secciones marcadas ✍️ con la experiencia real. Mantener este archivo actualizado
> durante el desarrollo: es la evidencia para la defensa.

## 1. Herramienta y tareas (indicador 18)

- **Herramienta:** Claude Code (agente de IA en la app de escritorio de Claude).
- **Cómo la guié:** antes de pedir código escribí la documentación que el agente lee:
  - `AGENTS.md` — stack, estructura, comandos, reglas de arquitectura, seguridad, validación y qué NO hacer.
  - `docs/spec.md` — qué hace la app, qué datos maneja y qué funciones incluye.
  - `docs/reglas-negocio.md` — fórmulas extraídas del prototipo HTML.
- **Tareas concretas encomendadas a la IA:**

| Tarea | Entrada que di | Resultado |
|---|---|---|
| Leer la rúbrica de defensa y el prototipo HTML | PDF + HTML | Resumen de requisitos y reglas de negocio |
| Crear la estructura del repositorio y la documentación | Pedido en lenguaje natural | Este árbol de archivos |
| ✍️ Implementar `calculo.py` | `reglas-negocio.md` + caso de oro | |
| ✍️ Implementar `db.py`, `validadores.py`, `pdf.py` | `spec.md`, `AGENTS.md` | |
| ✍️ Construir la UI Tkinter | `spec.md` §5 | |
| ✍️ Escribir pruebas | `AGENTS.md` §8 | |

## 2. Instrucciones, reglas y alcance dados al agente

Resumen de `AGENTS.md` (mostrar el archivo en la defensa):
- **Alcance:** solo app de escritorio local; sin red, login ni nube.
- **Reglas:** capas separadas, dinero con enteros/`Decimal`, SQL parametrizado, tipado y docstrings.
- **Límites:** no inventar reglas de negocio (preguntar), no tocar los archivos de referencia.

## 3. Patrones de seguridad incluidos y su verificación (indicador 19)

Ver [`seguridad.md`](seguridad.md). En breve: configuración en variables de entorno, validación de
entradas, SQL parametrizado, errores sin detalles técnicos, permisos mínimos, datos personales mínimos.

Verificación: pruebas automáticas (`tests/test_validadores.py`, `tests/test_db.py`) + prueba manual
con datos incorrectos durante la defensa.

## 4. Buenas prácticas y reflexión (indicador 20)

### Cómo revisé y probé el código generado
- Leí cada módulo antes de aceptarlo; no pegué código que no entendiera.
- Ejecuté `python -m pytest` tras cada cambio relevante.
- Comparé los resultados con el prototipo HTML (caso de oro).
- Probé manualmente entradas incorrectas en la interfaz.

### Bitácora de correcciones (completar con casos reales)

| Fecha | Qué generó la IA | Problema encontrado | Corrección |
|---|---|---|---|
| 24/11/2026 | Documentación inicial con valores de ejemplo (cuota 989.932, seguro 15.670, TAE 26,82 %) tomados del texto estático del HTML | Eran etiquetas de relleno, no resultados del cálculo | Ejecuté `calculateProforma` con Node, generé `tests/golden/referencia_html.json` y corregí los valores (991.072 / 15.489 / 38,88 %) |
| 24/11/2026 | `ui/app.py` pasaba el diccionario del cliente con claves `nombre`, mientras la BD espera `nombre_cliente` | `KeyError` al guardar; lo detectó el test de humo de la UI (`test_crud_completo`), no la lectura del código | Mapeo explícito de claves en `_datos_para_guardar` |
| 24/11/2026 | Test con expectativa `JOSE_ANDU` para "José Ñandú" | La Ñ se normaliza a N, no se elimina | Corregí el test a `JOSE_NANDU` |
| 24/11/2026 | Pruebas de UI creando y destruyendo una ventana Tk por test | Fallos intermitentes de Tk 8.6 en Windows (tests saltados al azar) | Una sola ventana por módulo, con reinicio de estado entre tests |
| 24/11/2026 | Botones rápidos de seguro en la misma fila que capital y plazo | Quedaban cortados en la captura de pantalla de la ventana | Los pasé a una segunda fila |
| ✍️ | | | |

Ejemplos típicos para tener en cuenta al revisar: redondeo bancario de Python vs. `Math.round` de
JavaScript; `float` en dinero; validación solo en la UI y no en el guardado; excepciones que muestran
traceback.

### Reflexión personal ✍️

- **Qué funcionó:** ✍️ (p. ej. documentar primero acelera y reduce errores de la IA)
- **Qué falló / tuve que corregir:** ✍️
- **Qué opino del uso de IA en el desarrollo:** ✍️ (la IA acelera, pero la responsabilidad de entender,
  probar y asegurar el código sigue siendo de quien programa)
