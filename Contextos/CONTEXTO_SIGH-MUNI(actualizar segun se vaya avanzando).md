
---

# 📘 CONTEXTO MAESTRO — CONTRACT FLOW



> Sistema Integrado de Gestión, Renovación y Trazabilidad de Contratos a Honorarios Municipales
> Última actualización: 2026-08-19
> Estado: **En desarrollo activo — Módulos core reestructurados y alineados al alcance actual**
> 
> 

---

## 1. RESUMEN EJECUTIVO



**Contract Flow** es una aplicación SaaS desarrollada para la Ilustre Municipalidad de Cunco que automatiza y agiliza el ciclo de vida completo y la renovación trimestral/anual de contratos a honorarios:

1. **Renovación / Creación Rápida:** Búsqueda en base de datos para clonar/renovar contratos de funcionarios en segundos, actualizando vigencias y cláusulas.


2. **Ingestión e Interpretación OCR de PDFs Escaneados:** Procesamiento con **PaddleOCR** / `pdfplumber` para extraer RUT, Nombre, N° Decreto, Correlativo, Montos, Vigencias y Cláusulas/Funciones de contratos físicos antiguos o digitalizados.


3. **Mapeo y Alertas de Entidades:** Verificación en tiempo real contra la base de datos local. Si el OCR detecta un prestador o unidad no existente, la interfaz despliega alertas de creación rápida mediante modales (`+ Nuevo Prestador`, `+ Nuevo Departamento`).


4. **Editor Dividido (Split-Screen) con Preview en Tiempo Real:** Formulario dinámico a la izquierda y visualización inmediata del contrato renderizado mediante Jinja2/HTML a la derecha.


5. **Dashboard, Trazabilidad e Historial por Funcionario:** Buscador global omnipresente y panel de historial completo para verificar cuántos contratos ha firmado cada prestador y su estado.


6. **Bitácora de Auditoría:** Registro inmutable de todas las acciones (creación, renovación, edición OCR, usuario responsable).



**Stack:** Flask 3.x + SQLite (WAL mode) + SQLAlchemy + Tailwind CSS (CDN) + Jinja2.

**Despliegue Target:** Railway con volumen persistente para SQLite y uploads.

**OCR:** PaddleOCR (v3.0+) + pdfplumber.

**PDF:** Generación HTML/Print-friendly + xhtml2pdf.

**Firma Digital y Pagos:** 100% Externalizados (El sistema genera el documento listo para firma; la gestión de liquidaciones de pagos se realiza a través del sistema SMC).

---

## 2. ARQUITECTURA DE CARPETAS



```
contract-flow-app/
├── app.py                      # Punto de entrada
├── seed.py                     # Datos iniciales (Departamentos, Usuarios, Prestadores, Contratos)
├── requirements.txt            # Dependencias Python
├── Procfile                    # Railway
├── data/
│   └── contract_flow.db        # SQLite persistente
├── app/
│   ├── __init__.py             # Application Factory, db, migrate
│   ├── config.py               # Configuración (UPLOAD_FOLDER, SECRET_KEY, DB path)
│   ├── auth/
│   │   ├── routes.py           # Login, Logout, Perfil
│   │   ├── utils.py            # @login_required, @role_required, get_current_user
│   │   └── forms.py            # Manejo de auth (opcional)
│   ├── models/
│   │   ├── __init__.py         # Importa todos los modelos
│   │   ├── user.py             # User, Department
│   │   ├── provider.py         # ServiceProvider (Prestadores)
│   │   ├── contract.py         # Contract, ContractFunction
│   │   └── audit.py            # AuditLog
│   ├── routes/
│   │   ├── __init__.py         # Registro de blueprints
│   │   ├── dashboard.py        # Panel principal, tabla de contratos e historial
│   │   ├── contract_builder.py # Renovador rápido, Split-Screen live preview y creador
│   │   ├── ocr_ingestion.py    # Subida de PDF escaneado + procesamiento PaddleOCR
│   │   └── search.py           # Buscador omnipresente (Ctrl + K)
│   ├── services/
│   │   ├── ocr_service.py      # Motor PaddleOCR + Parche Windows + Regex Parser
│   │   ├── pdf_generator.py    # Generación de contratos y vistas de impresión
│   │   └── audit_service.py    # log_action()
│   ├── static/
│   │   └── uploads/            # PDFs subidos (escaneos temporales y contratos finales)
│   └── templates/
│       ├── base.html           # Layout superior + Modal Buscador (Ctrl+K)
│       ├── auth/
│       │   └── login.html
│       ├── dashboard/
│       │   └── index.html      # Dashboard con métricas, historial y filtros
│       └── contracts/
│           ├── create.html     # Paso 1: Selección de Prestador / Carga de PDF OCR
│           ├── split_view.html # Paso 2: Editor Split-Screen (Formulario vs Preview Jinja2)
│           └── detail.html     # Ficha del contrato e historial unificado del funcionario
└── migrations/                 # Flask-Migrate / Alembic

```

---

## 3. MODELOS DE DATOS (SQLAlchemy)



### 3.1 departments



| Campo | Tipo | Notas |
| --- | --- | --- |
| id | PK int |  |
| code | TEXT UNIQUE | Ej: DIDECO, SECPLA, DOM, TRANSITO |
| name | TEXT | Nombre completo de la Unidad/Dirección |
| is_active | INT DEFAULT 1 |  |

### 3.2 users (RBAC)



| Campo | Tipo | Notas |
| --- | --- | --- |
| id | PK int |  |
| rut | TEXT UNIQUE | Usado para login |
| first_name, last_name | TEXT |  |
| email | TEXT UNIQUE |  |
| password_hash | TEXT | Werkzeug / bcrypt |
| role | TEXT CHECK | SUPERADMIN, ADMIN_RRHH, JEFE_DEPTO, AUDITOR |
| department_id | FK → departments |  |
| is_active | INT DEFAULT 1 |  |

### 3.3 service_providers



| Campo | Tipo | Notas |
| --- | --- | --- |
| id | PK int |  |
| rut | TEXT UNIQUE | RUT del Prestador a Honorarios |
| first_name, paternal_last_name, maternal_last_name | TEXT |  |
| email, phone, address | TEXT | Datos de contacto |
| profession_or_trade | TEXT | Profesión u Oficio registrado |

### 3.4 contracts



| Campo | Tipo | Notas |
| --- | --- | --- |
| id | PK int |  |
| provider_id | FK → service_providers |  |
| department_id | FK → departments |  |
| creation_type | TEXT DEFAULT 'CLONADO_BD' | 'NUEVO_MANUAL', 'CLONADO_BD' o 'PROCESADO_OCR' |
| contract_number | TEXT UNIQUE | Correlativo Ej: CH-2026-001 |
| decline_number | TEXT | N° Decreto Alcaldicio |
| decline_date | DATE | Fecha de emisión Decreto |
| position_title | TEXT | Cargo / Nombre del Servicio |
| program_name | TEXT | Programa municipal asociado |
| monthly_amount_gross | REAL | Monto mensual bruto $CLP |
| total_contract_amount | REAL | Monto total $CLP |
| start_date, end_date | DATE | Vigencia del contrato |
| pdf_file_path | TEXT | Ruta al PDF generado o cargado por OCR |
| ocr_processed | INT DEFAULT 0 | 0 = No, 1 = Sí |
| status | TEXT DEFAULT 'CREADO' | BORRADOR → CREADO → EN_EJECUCION → RENOVADO → FINALIZADO |

### 3.5 contract_functions



| Campo | Tipo | Notas |
| --- | --- | --- |
| id | PK int |  |
| contract_id | FK → contracts |  |
| function_order | INT | Orden correlativo (1, 2, 3...) |
| function_description | TEXT | Texto explícito de la cláusula/cometido |

---

## 4. MÓDULOS IMPLEMENTADOS ✅



### Módulo 01 — Autenticación y Dashboard



* **Rutas:** `/` (dashboard), `/auth/login`, `/auth/logout`

* **Funcionalidad:** Login por RUT/Email + contraseña. Control de acceso por roles (RBAC). Dashboard general con métricas, accesos rápidos a renovación y filtros de contratos.



### Módulo 02 — Ingestión OCR & Mapeo de Entidades



* **Rutas:** `/contracts/upload-ocr`

* **Funcionalidad:** Carga de documentos escaneados/digitalizados en PDF. Procesamiento por `PaddleOCR` (con parche Windows activo). Extracción de campos y verificación contra BD SQLite; despliegue de alertas modales si el Prestador o Departamento es nuevo.



### Módulo 03 — Editor Split-Screen y Renovación Rápida



* **Rutas:** `/contracts/builder`, `/contracts/<id>/renew`, `/contracts/<id>/split-view`

* **Funcionalidad:** Clonación de contrato previo para renovación trimestral. Editor dinámico en panel izquierdo (formulario + funciones) sincronizado en tiempo real con la vista previa Jinja2/HTML a la derecha.



---

## 5. MÓDULOS PENDIENTES / POR HACER 🔧



| Prioridad | Módulo | Descripción | Archivos a crear/modificar |
| --- | --- | --- | --- |
| 🔴 Alta | **Buscador Global (`Ctrl + K`)** | Modal omnipresente para localizar inmediatamente contratos por RUT, Nombre del funcionario, Decreto o Departamento. | `app/routes/search.py`, `templates/base.html`<br> |
| 🔴 Alta | **Optimización de Split-Screen Sync** | Renderizado del panel derecho vía API en Javascript sin parpadeos al modificar cláusulas/funciones dinámicas. | `templates/contracts/split_view.html`<br> |
| 🔴 Alta | **Filtros Históricos Avanzados** | Búsqueda por rango de fechas, montos brutos y estado de renovación en el Dashboard. | `app/routes/dashboard.py`<br> |
| 🟡 Media | **Ajustes de Expresiones Regulares en OCR** | Refinar el regex en `ocr_service.py` para mejorar el parsing automático de fechas de decretos y párrafos de cometidos. | `app/services/ocr_service.py`<br> |

---

## 6. FLUJOS DE TRABAJO (Cómo usar el sistema)



### Flujo 1: Renovación rápida de un contrato desde la Base de Datos



1. Ir al Dashboard (`/`) o presionar `Ctrl + K` y buscar al funcionario.
2. Hacer clic en **"🔄 Renovar Contrato"** sobre su último registro.


3. El sistema clona automáticamente los datos (RUT, Nombre, Depto, Montos, Cláusulas) y asigna un nuevo correlativo.


4. Abre el editor Split-Screen (`/contracts/<id>/split-view`) donde se actualizan únicamente la vigencia y/o nuevas funciones.


5. Guardar y generar el documento final listo para el proceso de firma.



### Flujo 2: Cargar contrato físico o escaneado mediante OCR



1. Clic en **"📤 Cargar PDF (OCR)"**.


2. Subir el contrato digitalizado.
3. El motor **PaddleOCR** analiza el archivo y extrae RUT, Decreto, Fechas, Montos y Cláusulas.
4. Si la entidad no existe, el sistema advierte en pantalla y permite crearla en 1 clic (`+ Nuevo Prestador` / `+ Nuevo Depto`).


5. Redirige al editor Split-Screen para verificar los datos leídos por OCR antes de guardar.



### Flujo 3: Rastrear historial completo de un funcionario



1. Presionar `Ctrl + K` desde cualquier pantalla.


2. Ingresar RUT o Nombre del prestador a honorarios (ej: "Juan Pérez").


3. El sistema despliega la lista cronológica con todos los contratos que el funcionario ha firmado con la municipalidad, sus montos e historia de renovaciones.



---

## 7. CONFIGURACIONES CRÍTICAS



### `app/services/ocr_service.py` (Parche Crítico de Windows Obligatorio)

```python
import os

# Desactivar ejecutor PIR que crashea PaddleOCR v3.0+ en entorno Windows
os.environ['FLAGS_enable_pir_in_executor'] = '0'
os.environ['FLAGS_enable_pir_api'] = '0'

from paddleocr import PaddleOCR
import pdfplumber
# ... resto de la lógica del OCR

```

### `app/config.py`

```python
import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-contract-flow-2026'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, '..', 'data', 'contract_flow.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'pdf'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max

```

### `requirements.txt`

```
Flask==3.0.3
Flask-SQLAlchemy==3.1.1
Flask-Migrate==4.0.7
Werkzeug==3.0.3
pdfplumber==0.11.0
paddleocr==2.7.3
pdf2image==1.17.0
Pillow==10.3.0
xhtml2pdf==0.2.15

```

---

## 8. DATOS DE PRUEBA (seed.py)



Credenciales para pruebas de desarrollo:

| Rol | Email | Contraseña | Departamento |
| --- | --- | --- | --- |
| ADMIN_RRHH | admin@contractflow.cl | admin123 | DIDECO |
| JEFE_DEPTO | jefe@contractflow.cl | jefe123 | DIDECO |
| AUDITOR | auditor@contractflow.cl | auditor123 | SECPLA |
| SUPERADMIN | super@contractflow.cl | super123 | DIDECO |

Entidades iniciales creadas:

* **Departamentos:** DIDECO, SECPLA, DOM, TRÁNSITO
* **Prestadores:** Juan Pérez González (RUT: 15.345.678-9), Ana Silva Rojas (RUT: 12.876.543-2)
* **Contratos:** CH-2026-001 (EN_EJECUCION), CH-2026-002 (FINALIZADO)

---

## 9. NOTAS TÉCNICAS Y REGLAS DEL PROYECTO



1. **Parche PaddleOCR en Windows:** Nunca remover las variables de entorno `FLAGS_enable_pir_...` en `ocr_service.py`, de lo contrario el proceso de Python fallará al inicializar PaddleOCR en entorno local bajo Windows.
2. **Relaciones SQLAlchemy:** `Contract` se relaciona directamente con `ServiceProvider`, `Department` y contiene una lista en cascada de `ContractFunction` (`cascade='all, delete-orphan'`).
3. **Persistencia e Historial:** La modificación o renovación de un contrato **nunca sobrescribe** el contrato anterior. Siempre crea un nuevo registro en la tabla `contracts` con referencia al historial del funcionario.
4. **Independencia de Pagos:** Este sistema se enfoca en la generación, ingestión y renovación rápida de contratos a honorarios. El circuito de aprobación financiera de pagos se gestiona externamente mediante SMC.

---

## 10. CHECKLIST PARA CONTINUAR DESARROLLO



* [ ] Asegurar que `app/services/ocr_service.py` incluya el parche Windows y la extracción Regex de cláusulas.
* [ ] Implementar la sincronización dinámica de `split_view.html` (JS Vanilla) para actualizar el documento previo al cambiar campos.
* [ ] Finalizar la barra del Buscador Global `Ctrl + K` en `base.html` y su ruta en `app/routes/search.py`.
* [ ] Verificar la correcta ejecución de `seed.py` generando la base de datos `data/contract_flow.db`.

---

*Documento actualizado y reestructurado para la continuidad del proyecto Contract Flow.*

*Sube este archivo como contexto inicial para cualquier prompt o sesión de trabajo.*