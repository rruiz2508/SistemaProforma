# Rúbrica de defensa final — Curso de Python (martes y jueves)

Defensa: **24/11/2026** · máx. **10 minutos** · 20 indicadores × 1 punto (todo o nada).
Fuente: `Rubrica_Defensa_Final_Python.pdf` (Prof. Rolando Fariña). Tipo de proyecto: **Aplicación de escritorio (Tkinter)**.

Estado: ⬜ pendiente · ✅ listo (actualizar al avanzar).

## A. Aplicación funcional (5)

| # | Indicador | Evidencia en este proyecto | Estado |
|---|---|---|---|
| 1 | Se ejecuta sin errores desde el inicio, siguiendo los pasos explicados | `README.md` (`python main.py`). Probar en entorno limpio antes de defender. | ⬜ |
| 2 | La función principal se demuestra en vivo con el resultado esperado | Cambiar capital/plazo → cuotero y totales se recalculan; generar PDF. | ✅ (probar en vivo) |
| 3 | Permite crear y consultar información | Guardar proforma → aparece en "Proformas guardadas"; buscador. | ⬜ |
| 4 | Permite modificar o eliminar sin errores | Editar → Actualizar; Eliminar con confirmación. | ⬜ |
| 5 | Interfaz comprensible para un usuario nuevo | Secciones numeradas 1–4, etiquetas claras, mensajes de ayuda. | ⬜ |

## B. Validación y manejo de errores (5)

| # | Indicador | Cómo se demuestra | Estado |
|---|---|---|---|
| 6 | Campos numéricos rechazan letras y símbolos | Escribir `abc` o `$#` en capital/cuotas/tasas: no se acepta. | ⬜ |
| 7 | Teléfono rechaza letras y valores inválidos (`000000`, longitudes imposibles) | Probar `abc`, `000000`, `123`, 30 dígitos. | ⬜ |
| 8 | Obligatorios no vacíos, con mensaje claro | Guardar con nombre/documento/teléfono vacíos. | ⬜ |
| 9 | Otros campos con formato propio validados (cédula, fecha, valor negativo…) | Documento inválido, fecha `31/02/2026`, capital `-5`/`0`. | ⬜ |
| 10 | Manejo seguro de cualquier entrada inesperada | Pegar texto larguísimo, emojis, `'; DROP TABLE--`: no se cierra, sin traceback. | ⬜ |

## C. Problema, comunicación y propuesta de valor (4)

| # | Indicador | Dónde preparar | Estado |
|---|---|---|---|
| 11 | Problema real y a quién va dirigida | `spec.md` §1, `guia-defensa.md` | ⬜ |
| 12 | Explicación simple, sin tecnicismos | `guia-defensa.md` (guion con analogías) | ⬜ |
| 13 | Menciona al menos una solución similar del mercado | `guia-defensa.md` §Competencia | ⬜ |
| 14 | Justifica qué la hace diferente o reconoce límites | `guia-defensa.md` §Diferencial y límites | ⬜ |

## D. Criterio de diseño y especificación (3)

| # | Indicador | Evidencia | Estado |
|---|---|---|---|
| 15 | Presenta un spec básico (qué hace, qué datos, qué funciones) | `docs/spec.md` | ✅ |
| 16 | Explica por qué eligió Tkinter | `docs/arquitectura.md` §3 | ✅ |
| 17 | Muestra código y estructura y cómo se ejecuta | `AGENTS.md` §3–4, `README.md`, `src/proformas/` | ✅ |

## E. Desarrollo y buenas prácticas con IA (3)

| # | Indicador | Evidencia | Estado |
|---|---|---|---|
| 18 | Herramienta de IA, tareas concretas y cómo la guió (spec.md y AGENT.md) | `AGENTS.md`, `docs/spec.md`, `docs/uso-de-ia.md` §1–2 | ✅ |
| 19 | Patrones de seguridad en las instrucciones y cómo se verificaron | `AGENTS.md` §6–7, `docs/seguridad.md` | ✅ |
| 20 | Revisó y probó el código; reflexión personal | `docs/uso-de-ia.md` §4 (completar ✍️) | ⬜ |

## Escala

18–20 Sobresaliente · 15–17 Muy bueno · 12–14 Satisfactorio · 9–11 En proceso · 0–8 Insuficiente.

> Nota: la rúbrica nombra el archivo `AGENT.md`; este repo usa `AGENTS.md` (convención más extendida).
> Es el "documentación equivalente" que menciona el indicador 18.
