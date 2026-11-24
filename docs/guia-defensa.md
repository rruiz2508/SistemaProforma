# Guía de defensa — 10 minutos

## Guion sugerido

| Min | Bloque | Qué decir / mostrar | Indicadores |
|---|---|---|---|
| 0:00–1:30 | **Problema y público** | "Un asesor de crédito tiene al cliente enfrente y necesita decirle cuánto pagará al mes. Hoy usa planillas: lento y con errores de redondeo, IVA y seguro. Mi app lo calcula al instante, lo guarda y entrega un PDF." | 11, 12 |
| 1:30–2:30 | **Mercado y diferencial** | Ver abajo. | 13, 14 |
| 2:30–3:30 | **Spec y por qué Tkinter** | Mostrar `docs/spec.md` (qué hace / datos / funciones) y la tabla de `arquitectura.md` §3. | 15, 16 |
| 3:30–6:30 | **Demo en vivo** | 1) Abrir la app. 2) Cambiar capital y plazo → se recalcula. 3) Guardar con datos del cliente. 4) Aparece en la lista; buscar. 5) Editar y actualizar. 6) Generar PDF. 7) Eliminar (confirmar). | 1–5 |
| 6:30–8:00 | **Validación** | Letras en capital; teléfono `000000`; campos vacíos; fecha inválida; `'; DROP TABLE--` como nombre. La app responde con mensajes, no se cierra. | 6–10 |
| 8:00–9:00 | **Código y estructura** | Árbol de `AGENTS.md` §3; mostrar `calculo.py` (puro) vs `ui/`; `python -m pytest` en verde. | 17 |
| 9:00–10:00 | **IA, seguridad y reflexión** | `AGENTS.md` + `spec.md` como guía; patrones de `seguridad.md`; qué falló y qué corregí; opinión. | 18, 19, 20 |

## Explicación sin tecnicismos (analogía)

"Es como una calculadora especializada para préstamos: le digo cuánto quiero, en cuántos meses, y me
arma la tabla con cada cuota, cuánto es capital, cuánto interés, impuesto y seguro. Además deja
archivada cada cotización y me imprime el comprobante en PDF."

## Competencia (indicador 13)

- **Simuladores de préstamos de bancos** y de sitios financieros (web, genéricos).
- **Planillas de Excel / Google Sheets** con la función PAGO (la herramienta que usa hoy la mayoría).
- Sistemas de gestión de créditos completos (core financiero).

## Diferencial y límites (indicador 14)

**Diferencial:** reglas propias de la institución (gastos administrativos con IVA, seguro nivelado,
traslado de vencimientos a día hábil, T.A.E. real), N.º de operación automático, historial con
búsqueda y PDF con identidad de la institución, todo **sin internet** y sin instalar servidores.

**Límites honestos:** un solo usuario por PC; sin login; BD local sin cifrar; no se integra con el sistema
contable; solo guaraníes; el cálculo replica el prototipo y debe validarse contra el área financiera.

## Preguntas probables del docente

- *¿Por qué Tkinter y no Django?* → App local de un usuario; Django exige servidor, sesiones y navegador. (`arquitectura.md` §3)
- *¿Cómo evitas inyección SQL?* → Consultas con `?`; hay un test que lo prueba.
- *¿Qué hace la IA y qué haces tú?* → Yo definí spec y reglas; la IA generó borradores; yo revisé, probé y corregí (bitácora).
- *¿Qué pasa si escriben letras en el capital?* → Se bloquean al teclear y se vuelven a validar al guardar.
- *¿Dónde se guardan los datos?* → `data/proformas.db` (SQLite), local, fuera de git.

## Lista de verificación previa (hacer ANTES de las 19:00)

- [ ] Clonar/copiar el proyecto en una carpeta nueva y ejecutar los pasos del README desde cero.
- [ ] `python -m pytest` en verde (106 pruebas).
- [ ] Mostrar el caso de oro: 10.000.000 · 12 cuotas · 24 % → cuota Gs. 991.072.
- [ ] Tener 2–3 proformas de ejemplo guardadas (sin datos reales de clientes).
- [ ] Un PDF de ejemplo ya generado por si falla el visor.
- [ ] Completar ✍️ de `docs/uso-de-ia.md` (bitácora y reflexión).
- [ ] Tener abiertos: `AGENTS.md`, `docs/spec.md`, la app y una terminal.
