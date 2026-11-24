# Reglas de negocio — Cálculo de la proforma

Extraídas de `Cálculo Proforma Asesor Comercial.html` (función `calculateProforma`). Esta es la
referencia que debe implementar `src/proformas/calculo.py`.

## 1. Tasas

```
i_mensual     = (TAN / 100) / 12
i_mensual_iva = i_mensual × (1 + IVA)
TAN_con_IVA   = TAN × (1 + IVA)
```

## 2. Cuota base (Método Francés, sin gastos)

Sobre la tasa mensual **con IVA**:

```
si i_mensual_iva > 0:
    cuota_sin_gasto = capital × i·(1+i)^n / ((1+i)^n − 1)      con i = i_mensual_iva
si no:
    cuota_sin_gasto = capital / n
```

## 3. Gastos administrativos

```
g_adm_base    = capital × pct_gastos / 100
g_adm_iva     = g_adm_base × IVA
g_adm_total   = g_adm_base + g_adm_iva
g_adm_mensual = g_adm_total / n          (prorrateado)
```
En la última cuota se cobra el saldo remanente de gastos (cierra en 0).

## 4. Fechas

- Fecha de desembolso (D) y primer vencimiento (V1).
- Todo vencimiento que cae **sábado → +2 días**, **domingo → +1 día** (lunes hábil).
- Suma de meses conserva el día; si no existe (31 → febrero) usa el último día del mes.
- Cuota k (k ≥ 2): `ancla + (k−1) meses`, luego ajuste hábil.
- `dias_primer_vto = V1_hábil − D` y se descuentan los días trasladados por fin de semana.
- `dias_excedentes = max(0, dias_computables − 30)`.

### 4.1 Interés por días extra (primer período > 30 días)

Si hay `dias_excedentes > 0` y el V1 es posterior al habitual (D + 1 mes):

- **Regla legado** (`LEGACY_MES_EXTRA_PRIMER_VTO = True`): se cobran los meses completos hasta el
  ancla **+ 1 mes extra**, sobre `capital + g_adm_total`:
  `interes_extra_base = i_mensual × ((capital + g_adm_total) × meses_primer_periodo − capital)`
- Si no aplica la regla legado: `interes_extra_base = capital × (i_mensual / 30) × dias_excedentes`.

```
iva_extra            = interes_extra_base × IVA
extra_total          = interes_extra_base + iva_extra
extra_base_por_cuota = interes_extra_base / n          (se reparte en las n cuotas)
extra_total_por_cuota= extra_total / n
```

## 5. Seguro nivelado

Seguro mensual sobre el saldo de capital de cada período, con IVA, **promediado** para que todas las
cuotas lleven el mismo seguro:

```
seguro_k = saldo_inicial_k × tasa_seguro/100 × (1 + IVA)
seguro_nivelado = (Σ seguro_k, k=1..n) / n
```
Para el cálculo del seguro se amortiza el capital con `amort_k = min(saldo, cuota_sin_gasto − int_k − iva_int_k)`.
Si el primer vencimiento fue modificado, el primer período usa `capital + g_adm_total` como base.

Redondeo del seguro (modo entero): `round(seguro_exacto)`; si V1 modificado: `round(seg/(1+IVA))` + `round(... × IVA)`.

## 6. Cuota final de referencia

```
cuota_base_gastos = cuota_sin_gasto + g_adm_mensual + extra_total_por_cuota
cuota_final_ref   = cuota_base_gastos + seguro_nivelado
```
Modo entero: se redondea el resultado (`round`), no cada sumando.

## 7. Cuotero (fila k = 1..n)

```
saldo_inicial_k = saldo_final_{k-1}      (saldo_inicial_1 = capital)
interes_k       = round( saldo_inicial_k × i_mensual + extra_base_por_cuota )
iva_k           = round( (saldo_inicial_k × i_mensual + extra_base_por_cuota) × IVA )
g_adm_k         = g_adm_mensual            (k < n)   |  gastos pendientes (k = n)
seguro_k        = seguro_nivelado
cuota_final_k   = cuota_final_ref          (k < n)
amort_cap_k     = cuota_final_k − seguro_k − g_adm_k − interes_k − iva_k   (acotado a [0, saldo])
saldo_final_k   = saldo_inicial_k − amort_cap_k
```
**Última cuota (k = n):** `amort_cap_n = saldo_inicial_n` (+ ajuste de redondeo al millar si V1
modificado y modo entero). El residuo de redondeo (≤ máx(5, 0,5 % de la cuota)) se absorbe en el
interés de esa cuota para que `cuota_final_n = cuota_final_ref`. El saldo final cierra en **0**.

Totales: suma de cada columna. `Total a pagar = Σ cuota_final_k`.

## 8. T.A.E. (Tasa Anual Efectiva)

Tasa `r` tal que el valor presente de los pagos iguala lo recibido:

```
Σ pago_k / (1 + r)^(dias_k / 365)  =  capital
pago_k = amort_cap_k + interes_k + g_adm_k + iva_k + seguro_k
```
Se resuelve por **bisección** en [0, 10] con 100 iteraciones; días = `fecha_k − desembolso`.
Si el VP con r = 0 ya es ≤ capital, TAE = 0. Resultado en %.

## 9. Redondeo

| Modo | Efecto |
|---|---|
| Institucional (entero) | Todos los importes en Gs. enteros (`round` half-up). |
| Exacto | Dos decimales (`Decimal.quantize`). |

> **Nota Python:** el `round()` de Python usa redondeo bancario (half-even). Para igualar a
> `Math.round` de JavaScript (half-up) usar `decimal.Decimal(...).quantize(1, ROUND_HALF_UP)`.

## 10. Valor de referencia ("caso de oro")

Capital 10.000.000 · 12 cuotas · TAN 24 % · IVA 10 % · gastos 2 % · seguro 0,25 % · redondeo entero ·
desembolso con 1er vencimiento a +1 mes:

| Indicador | Valor (ejecutando el HTML) |
|---|---|
| Cuota final mensual | Gs. 991.072 |
| Seguro nivelado | Gs. 15.489 |
| Gasto adm. (total / mensual) | Gs. 220.000 / Gs. 18.333 |
| Total a pagar | Gs. 11.892.864 |
| TAE | 38,88 % |

> Los números que muestra el HTML sin ejecutar (989.932, 15.670, 26,82 %) son texto estático de
> ejemplo, no resultados del cálculo. Los valores de esta tabla salen de ejecutar `calculateProforma`.
> `tests/golden/referencia_html.json` contiene 8 escenarios generados así (incluye 1er vencimiento
> modificado, n = 1, tasa 0 %, n = 120 y modo exacto) y `tests/test_calculo.py` verifica que Python
> reproduce cada cuota del cuotero.
