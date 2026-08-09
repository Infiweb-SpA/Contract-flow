# 📘 CONTEXTO MAESTRO — SIGH-MUNI
> Sistema Integrado de Gestión, Creación y Revisión de Honorarios Municipales
> Última actualización: 2026-08-08
> Estado: **En desarrollo activo — Módulos core funcionales**

---

## 1. RESUMEN EJECUTIVO

SIGH-MUNI es una aplicación SaaS para municipalidades chilenas que gestiona el ciclo de vida completo de contratos a honorarios y el flujo de autorización de sus pagos mensuales:

1. **Creación** de contratos desde plantillas tipo (con funciones dinámicas).
2. **Ingestión** de contratos externos firmados en plataforma municipal (PDF + OCR para extraer funciones).
3. **Buscador Global Omnipresente (`Ctrl + K`)** para trazabilidad inmediata y localización de contratos/pagos.
4. **Revisión** en vista dividida (Split-View: editor/checklist de funciones + visor PDF).
5. **Flujo de aprobación de pagos mensuales** basado en las 4 etapas internas de RRHH sobre contratos firmados.
6. **Bitácora de auditoría** inmutable de todas las acciones.

**Stack:** Flask 3.x + SQLite (WAL) + SQLAlchemy + Tailwind CSS (CDN) + Jinja2.  
**Despliegue target:** Railway con volumen persistente para SQLite y PDFs.  
**OCR:** pdfplumber (PDFs nativos) / PaddleOCR (PDFs escaneados).  
**PDF:** xhtml2pdf (generación server-side) + `window.print()` (vista previa navegador).  
**Firma Digital:** 100% Externalizada (el sistema no realiza ni valida firmas digitales).

---

## 2. ARQUITECTURA DE CARPETAS

```
muni-sigh-app/
├── app.py                      # Punto de entrada
├── seed.py                     # Datos de prueba (4 usuarios, 2 contratos, 1 pago)
├── requirements.txt            # Dependencias Python
├── Procfile                    # Railway
├── data/
│   └── sigh_muni.db            # SQLite persistente
├── app/
│   ├── __init__.py             # Application Factory, db, migrate
│   ├── config.py               # Configuración (UPLOAD_FOLDER, SECRET_KEY, etc.)
│   ├── auth/
│   │   ├── routes.py           # Login, Logout, Perfil
│   │   ├── utils.py            # @login_required, @role_required, get_current_user
│   │   └── forms.py            # (vacío, no se usa WTForms aún)
│   ├── models/
│   │   ├── __init__.py         # Importa todos los modelos
│   │   ├── user.py             # User, Department
│   │   ├── provider.py         # ServiceProvider
│   │   ├── contract.py         # Contract, ContractFunction
│   │   ├── payment.py          # MonthlyPayment, PaymentFunctionChecklist
│   │   └── audit.py            # AuditLog
│   ├── routes/
│   │   ├── __init__.py         # Registro de blueprints
│   │   ├── dashboard.py        # Panel de control + indicadores
│   │   ├── contract_builder.py # Crear, editar, detalle, preview, upload OCR
│   │   ├── payments.py         # Bandeja, revisión, aprobación 4 niveles RRHH
│   │   └── search.py           # Buscador global omnipresente (Ctrl + K)
│   ├── services/
│   │   ├── pdf_generator.py    # generate_contract_html, generate_contract_pdf, make_pdf_response
│   │   ├── ocr_service.py      # extract_text_from_pdf (pdfplumber + PaddleOCR fallback)
│   │   └── audit_service.py    # log_action()
│   ├── static/
│   │   └── uploads/            # PDFs subidos (informes, contratos externos firmados)
│   └── templates/
│       ├── base.html           # Layout con navegación superior + Modal Buscador (Ctrl+K)
│       ├── auth/
│       │   └── login.html
│       │   └── profile.html    # Perfil de usuario
│       ├── dashboard/
│       │   └── index.html      # Panel de control + tabla contratos
│       ├── contracts/
│       │   ├── create.html     # Armador de contratos + modales prestador/depto
│       │   ├── detail.html     # Ficha completa del contrato + acciones
│       │   ├── edit.html       # Split-View editor de funciones
│       │   ├── upload.html     # Carga de contrato externo + OCR
│       │   └── pdf_template.html # Plantilla HTML oficial del contrato (impresión)
│       └── payments/
│           ├── bandejas.html   # Tabla de pagos mensuales con filtros por etapa RRHH
│           ├── review.html     # Checklist de funciones + circuito de aprobación en 4 niveles
│           └── split_view.html # Validación de informe (subir PDF + OCR)
└── migrations/                 # Flask-Migrate / Alembic
```

---

## 3. MODELOS DE DATOS (SQLAlchemy)

### 3.1 departments
| Campo | Tipo | Notas |
|---|---|---|
| id | PK int | |
| code | TEXT UNIQUE | Ej: DIDECO, SECPLA, DOM |
| name | TEXT | Nombre completo |
| cost_center | TEXT | Opcional |
| is_active | INT DEFAULT 1 | |

### 3.2 users (RBAC)
| Campo | Tipo | Notas |
|---|---|---|
| id | PK int | |
| rut | TEXT UNIQUE | Usado para login |
| first_name, last_name | TEXT | |
| email | TEXT UNIQUE | |
| password_hash | TEXT | bcrypt/Werkzeug |
| role | TEXT CHECK | SUPERADMIN, RRHH_NIVEL_1, RRHH_NIVEL_2, RRHH_NIVEL_3, RRHH_NIVEL_4, JEFE_DEPTO |
| department_id | FK → departments | |
| is_active | INT DEFAULT 1 | |

### 3.3 service_providers
| Campo | Tipo | Notas |
|---|---|---|
| id | PK int | |
| rut | TEXT UNIQUE | |
| first_name, paternal_last_name, maternal_last_name | TEXT | |
| email, phone, address | TEXT | |
| bank_name, account_type, account_number | TEXT | Datos bancarios |

### 3.4 contracts
| Campo | Tipo | Notas |
|---|---|---|
| id | PK int | |
| provider_id | FK → service_providers | |
| department_id | FK → departments | |
| creation_type | TEXT DEFAULT 'CREADO' | 'CREADO' o 'CARGADO_EXTERNO' |
| contract_number | TEXT UNIQUE | Correlativo Ej: CT-2026-0809 |
| decline_number | TEXT | N° Decreto Alcaldicio |
| decline_date | DATE | |
| position_title | TEXT | Cargo |
| program_name | TEXT | Programa municipal |
| monthly_amount_gross | REAL | Monto mensual CLP |
| total_contract_amount | REAL | |
| start_date, end_date | DATE | Vigencia |
| pdf_file_path | TEXT | Ruta al PDF firmado externamente |
| ocr_processed | INT DEFAULT 0 | 0/1 |
| status | TEXT DEFAULT 'INGRESADO' | BORRADOR → INGRESADO → EN_EJECUCION → FINALIZADO |

---

## 4. MÓDULOS IMPLEMENTADOS ✅

### Módulo 01 — Autenticación y Dashboard
- **Rutas:** `/` (dashboard), `/auth/login`, `/auth/logout`, `/auth/profile`
- **Funcionalidad:** Login por RUT/Email + contraseña. Sesiones Flask. Roles RBAC. Dashboard con métricas e indicadores.

### Módulo 02 — Ingestión y Armador de Contratos
- **Rutas:** `/contracts/create`, `/contracts/upload`
- **Funcionalidad:** Armador de plantillas e Ingestión OCR de PDFs firmados externamente con `pdfplumber` / `PaddleOCR`.

### Módulo 03 — Detalle, Edición y Vista Previa
- **Rutas:** `/contracts/<id>`, `/contracts/<id>/edit`, `/contracts/<id>/preview`
- **Funcionalidad:** Ficha completa, edición Split-View y vista previa de impresión HTML/PDF.

### Módulo 04 — Flujo de Aprobación de Pagos Mensuales
- **Rutas:** `/payments/`, `/payments/<id>/review`, `/payments/<id>/approve`
- **Funcionalidad:** Circuitos de revisión en 4 niveles de RRHH con checklist de funciones e informes adjuntos.

---

## 5. MÓDULOS PENDIENTES / POR HACER 🔧

| Prioridad | Módulo | Descripción | Archivos a crear/modificar |
|---|---|---|---|
| 🔴 Alta | **Buscador Global (`Ctrl + K`)** | Modal omnipresente para localizar contratos y pagos por RUT, Nombre, N° Contrato, Decreto o Depto. Muestra ubicación exacta y tiempo de estancamiento. | `app/routes/search.py`, `templates/base.html` |
| 🔴 Alta | **Split-View Editor real** | Visor dividido (PDF a la izquierda, checklist/formulario a la derecha) para revisión de contratos e informes. | `app/templates/contracts/edit.html` |
| 🔴 Alta | **Paginación y Alertas** | Paginación de tablas y etiquetas de advertencia en pagos estancados por más de 5 días. | `dashboard.py`, `payments.py` |
| 🟡 Media | **Mejorar parser OCR** | Optimización de extracción de funciones y datos con expresiones regulares. | `app/services/ocr_service.py` |

---

## 6. FLUJOS DE TRABAJO (Cómo usar el sistema)

### Flujo 1: Cargar contrato externo (firmado en plataforma municipal)
1. Dashboard → clic "📤 Cargar Externo" (`/contracts/upload`).
2. Subir el PDF del contrato ya firmado por autoridades en el sistema externo.
3. Sistema ejecuta OCR automáticamente y extrae cláusulas y funciones.
4. Redirige a Split-View (`/contracts/<id>/edit`) para validar o ajustar funciones.

### Flujo 2: Aprobar pago mensual (4 Etapas RRHH)
1. Ingesta de informe de actividades del mes para un contrato en ejecución.
2. Expediente ingresa a **Bandeja RRHH - Nivel 1** (Recepción y Verificación).
3. **RRHH Nivel 2:** Evaluación ítem por ítem del checklist de funciones (`Cumplido`, `Parcial`, `No Cumplido`).
4. **RRHH Nivel 3:** Visado administrativo y verificación de liquidación/montos.
5. **RRHH Nivel 4:** Aprobación final y liberación para pago en Finanzas/Tesorería.

### Flujo 3: Rastrear contrato o pago "Perdido en el aire"
1. En cualquier pantalla, presionar `Ctrl + K`.
2. Escribir el RUT del prestador, nombre (ej. "Juan Pérez"), departamento (ej. "DIDECO") o N° de Decreto.
3. El sistema muestra de inmediato la ficha con la **Ubicación Exacta** (ej. *En escritorio de: RRHH Nivel 2 - Hace 4 días*) y botón directo al expediente.

---

## 7. CONFIGURACIONES CRÍTICAS

### `app/config.py` (verificar que exista)
```python
import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-cambiar-en-produccion'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or         'sqlite:///' + os.path.join(basedir, '..', 'data', 'sigh_muni.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'pdf'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
```

### `requirements.txt` (librerías clave)
```
Flask==3.0.3
Flask-SQLAlchemy==3.1.1
Flask-Migrate==4.0.7
Flask-WTF==1.2.1
WTForms==3.1.2
Werkzeug==3.0.3
pdfplumber==0.11.0
paddleocr==2.7.3
pdf2image==1.17.0
Pillow==10.3.0
xhtml2pdf==0.2.15
```
> **NO usar WeasyPrint** — requiere dependencias del sistema (GTK/Pango/Cairo). Usar xhtml2pdf.

---

## 8. DATOS DE PRUEBA (seed.py)

Credenciales para probar el circuito completo:

| Rol | Email | Contraseña | Departamento |
|---|---|---|---|
| ADMIN_RRHH | admin@munisigh.cl | admin123 | DIDECO |
| JEFE_DEPTO | jefe@munisigh.cl | jefe123 | DIDECO |
| FINANZAS_CONTROL | finanzas@munisigh.cl | finanzas123 | SECPLA |
| SUPERADMIN | super@munisigh.cl | super123 | DIDECO |

Entidades creadas:
- **Departamentos:** DIDECO, SECPLA, DOM
- **Prestadores:** Juan Pérez González (aseo), Ana Silva Rojas (técnica)
- **Contratos:** CT-2026-001 (técnico, EN_EJECUCION), CT-2026-0809 (aseo, FINALIZADO)
- **Pago:** Agosto 2026 para CT-2026-001 (PENDIENTE_REVISION)

---

## 9. NOTAS TÉCNICAS Y PROBLEMAS CONOCIDOS

1. **Relaciones SQLAlchemy:** `MonthlyPayment` debe tener `contract = db.relationship('Contract', back_populates='payments')` y `Contract` debe tener `payments = db.relationship('MonthlyPayment', back_populates='contract')`. Si falta, la bandeja falla con `UndefinedError: 'MonthlyPayment' has no attribute 'contract'`.

2. **Estados de contrato:** El modelo usa `BORRADOR → CREADO_PARA_FIRMA → INGRESADO → EN_EJECUCION → FINALIZADO`. El esquema SQL original tenía `CREADO` pero se unificó a `CREADO_PARA_FIRMA`.

3. **Filtros de bandeja:** "Mi Bandeja" (sin filtro) muestra pendientes del rol. Los filtros de estado (Pendientes, Aprobados, etc.) muestran **historial completo** de ese estado sin importar el rol.

4. **OCR básico:** La extracción de funciones por heurística busca palabras clave (`función`, `cometido`, `deber`, `tarea`) en las primeras 15 líneas del texto. Es mejorable.

5. **PDF:** La vista previa usa `pdf_template.html` con `window.print()` para generar PDF desde el navegador. La descarga usa xhtml2pdf.

6. **Base de datos:** Si se cambian modelos, ejecutar:
   ```bash
   flask db migrate -m "descripcion"
   flask db upgrade
   ```
   O en desarrollo: borrar `data/sigh_muni.db` y reejecutar `python seed.py`.

---

## 10. CHECKLIST PARA CONTINUAR DESARROLLO

- [ ] Crear `app/templates/contracts/edit.html` como **Split-View real** (visor PDF embebido + editor de funciones).
- [ ] Agregar paginación en `dashboard/index.html` y `payments/bandejas.html`.
- [ ] Mejorar `ocr_service.py` con regex para extraer RUT, montos, fechas decretos.
- [ ] Crear módulo de administración de usuarios (`/admin/users`).
- [ ] Crear módulo de administración de departamentos (`/admin/departments`).
- [ ] Agregar reportes/exportes Excel.
- [ ] Tests de integración para el circuito de aprobación de pagos.
- [ ] Revisar responsive design en móviles (actualmente optimizado para desktop).

---

*Documento generado para continuidad del proyecto SIGH-MUNI.*
*Si se resetea la conversación, subir este archivo como contexto inicial.*
