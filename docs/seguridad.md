# Patrones de seguridad y cómo se verifican (indicador 19)

Estos patrones están incluidos como instrucciones en `AGENTS.md` y se comprueban con pruebas o con
una revisión manual documentada.

| # | Patrón | Cómo se aplica | Cómo se verifica |
|---|---|---|---|
| S1 | **Configuración y secretos en variables de entorno** | `config.py` lee `PROFORMAS_*` desde el entorno / `.env`. `.env` está en `.gitignore`; se versiona solo `.env.example`. La app no usa claves de terceros. | `git ls-files \| findstr .env` solo debe listar `.env.example`. `grep -rn "C:\\\\Users"` en `src/` sin resultados. |
| S2 | **SQL parametrizado** | Todas las consultas en `db.py` usan `?`. Nunca f-strings con datos. | Test `test_db.py::test_sql_injection_es_dato`: guardar `Robert'); DROP TABLE proformas;--` como nombre y verificar que la tabla sigue existiendo y el texto se guardó literal. Revisión: `grep -n "execute(f" src/` sin resultados. |
| S3 | **Validación de entradas (lista blanca)** | `validadores.py` acepta solo lo permitido (dígitos, rangos, longitudes). La UI filtra al teclear (`validatecommand`) y se re-valida al guardar. Segunda barrera: `CHECK` en la tabla. | `tests/test_validadores.py` (letras, símbolos, `000000`, vacíos, negativos, fechas inválidas, texto muy largo). Prueba manual en la defensa. |
| S4 | **No exponer errores técnicos** | Excepciones capturadas en la frontera de UI; detalle al log (`data/app.log`), mensaje comprensible al usuario. `report_callback_exception` sobreescrito. | Forzar un error (p. ej. BD de solo lectura): se muestra "No se pudo guardar. Intente nuevamente" y no hay traceback. |
| S5 | **Permisos mínimos / sin red** | La app solo escribe en `data/`. No abre sockets ni hace peticiones HTTP. | Revisión de imports: no `requests`, `urllib`, `socket`. |
| S6 | **Saneo de nombres de archivo (anti path-traversal)** | El PDF se nombra `Proforma_<nro_operacion>_<CLIENTE_SANEADO>.pdf` con solo `[A-Z0-9_]`. | Test: nombre `../../Windows/x` produce un nombre seguro dentro de `data/pdf/`. |
| S7 | **Datos personales mínimos** | Solo nombre, documento, teléfono, observaciones. No se registran en logs. `data/*.db` y `data/pdf/` ignorados por git. | Revisar `git status` tras usar la app; revisar `data/app.log`. |
| S8 | **Operaciones destructivas con confirmación** | Eliminar pide confirmación con el N° de operación y el cliente. | Prueba manual: cancelar no borra. |
| S9 | **Dependencias mínimas y fijadas** | Solo `reportlab` (y `pytest` en desarrollo). `requirements.txt` con versión mínima. | `pip list` / `pip audit` (opcional) antes de la entrega. |
| S10 | **Revisión del código generado por IA** | Todo código de IA se lee, se ejecuta y se prueba antes de aceptarlo (ver `uso-de-ia.md`). | Historial git + bitácora. |

## Qué es un dato "sensible" aquí

Documento de identidad y teléfono del cliente. Por eso: la BD es local, no se sube al repositorio, no se
imprime en consola y el PDF se guarda solo en la carpeta local configurada.

## Riesgos conocidos / límites honestos

- La BD no está cifrada (SQLite en claro): se asume una PC de oficina con acceso controlado.
- No hay control de usuarios: cualquiera con acceso a la PC puede abrir la app.
- Mitigación futura: cifrado de disco (BitLocker) o SQLCipher; login por usuario.
