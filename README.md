# Sistema de Proformas — Fundación Industrial

Aplicación de escritorio (Python + Tkinter) para calcular proformas de préstamos con **Método Francés**,
gastos administrativos, IVA y seguro nivelado. Guarda en **SQLite** y genera el **cuotero en PDF**.

> Proyecto final del curso de Python (defensa 24/11/2026). Migración a Python del prototipo web
> `Cálculo Proforma Asesor Comercial.html`.

## Requisitos

- Windows 10/11 · Python 3.11 o superior (con Tkinter, incluido en el instalador oficial)

## Instalación y ejecución

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # opcional: la app funciona con valores por defecto
python main.py
```

Pruebas (106 en total):

```powershell
python -m pytest
```

Los datos se guardan en `data/proformas.db` y los PDF en `data/pdf/` (ambos fuera de git).

## Documentación

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

## Estado

Implementada: cálculo (verificado contra el prototipo HTML en 8 escenarios), validaciones,
CRUD en SQLite, PDF con reportlab e interfaz Tkinter.
