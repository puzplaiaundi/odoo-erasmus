# Plan de limpieza segura - gestion_erasmus

Este documento propone una limpieza por fases para eliminar archivos no usados
sin romper la carga del módulo.

## Estado actual

El módulo solo carga explícitamente los XML listados en `__manifest__.py` y solo
importa los modelos listados en `models/__init__.py`.

Consecuencia: varias piezas (controladores, hooks, assets, reportes y vistas)
están presentes en el árbol, pero no se ejecutan ni cargan en runtime.

## Fase 1 (segura): limpieza técnica

Eliminar archivos de caché Python (`__pycache__`, `*.pyc`) y ficheros vacíos o
placeholder sin impacto funcional.

### Objetivos

- Reducir ruido del repositorio.
- Evitar falsos positivos en análisis de uso.
- No afectar comportamiento de Odoo.

### Candidatos

- Todos los `__pycache__/` dentro de `addons/gestion_erasmus`.
- `views/users.xml` (está vacío: `<data/>`).

## Fase 2 (segura con validación): eliminar código no conectado

Eliminar archivos no referenciados por `__manifest__.py` ni por imports activos.

### Candidatos principales

- `controllers.py`
- `controllers/__init__.py`
- `controllers/controllers.py`
- `controllers/direccion_autocomplete.js`
- `hooks.py`
- `models/models.py`
- `models/users.py`
- `models/views.xml`
- `views/assets.xml`
- `views/templates.xml`
- `views/views.xml`
- `report/erasmus_persona_contract_report.xml`
- `data/ciclos.xml`
- `data/codigos.xml`
- `data/paises.xml`
- `demo/demo.xml`

### Nota

Si en el futuro se quiere usar portal, hooks, reportes o assets, estos archivos
pueden restaurarse desde Git.

## Fase 3 (opcional): material de referencia

Mover o eliminar archivos de apoyo no runtime:

- `report/reference/*`
- `README_LOGO.md`
- `static/src/pdf/README.md`

Recomendación: mover primero a una carpeta `docs/legacy/` antes de borrar.

## Validación recomendada tras cada fase

1. Reiniciar contenedores/servicio Odoo.
2. Actualizar módulo `gestion_erasmus` (`-u gestion_erasmus`).
3. Verificar:
   - apertura de menú y vistas cargadas;
   - formulario de `res.partner` con pestaña Erasmus;
   - creación/edición de registros en catálogos Erasmus.

## Comandos PowerShell de ayuda

### Listar y eliminar `__pycache__`

```powershell
Get-ChildItem addons/gestion_erasmus -Recurse -Directory -Filter __pycache__ |
  Remove-Item -Recurse -Force
```

### Listar y eliminar `*.pyc`

```powershell
Get-ChildItem addons/gestion_erasmus -Recurse -File -Filter *.pyc |
  Remove-Item -Force
```

### Ver cambios antes de commit

```powershell
git status --short
```

## Estrategia de commit sugerida

- Commit 1: "chore(gestion_erasmus): remove pycache artifacts"
- Commit 2: "chore(gestion_erasmus): remove unreferenced legacy files"
- Commit 3 (opcional): "docs(gestion_erasmus): archive reference assets"
