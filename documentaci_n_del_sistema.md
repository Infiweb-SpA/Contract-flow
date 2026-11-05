# Contract-flow (SIGH-MUNI)

**SIGH-MUNI** - Sistema Integrado de Gestión, Creación, Trazabilidad y Revisión de Honorarios Municipales

## Visión General

SIGH-MUNI es una solución SaaS integral diseñada para resolver el ciclo de vida completo de los contratos a honorarios y sus estados de pago en municipalidades de Chile. El sistema permite **armar y confeccionar nuevos contratos a honorarios** a partir de plantillas estandarizadas y decretos previos vigentes, así como **revisar, auditar y desglosar contratos existentes** subidos al sistema.

Diseñado con un enfoque estricto en la probidad y la trazabilidad requerida por la Contraloría General de la República (CGR), el sistema gestiona la cadena documental completa: desde la selección de decretos alcaldicios de respaldo (VISTOS) hasta el seguimiento puntual de aperturas, impresiones físicas, rúbricas de gestión y liberaciones financieras de pago.

---

## Flujo del Sistema y Ciclo de Vida Documental

### 1. **Definición de Antecedentes Legales y Decretos Previos (VISTOS)**
- Precarga automática del catálogo maestro de **Decretos Anuales Estandarizados** (Presupuesto municipal vigente, desagregación presupuestaria, POA, decretos de subrogancia de Alcaldía y Dirección de Control).
- Selección e integración dinámica de **decretos y antecedentes específicos del prestador** (Ficha de ingreso RRHH, contrato anterior del prestador, programas de delegaciones).

### 2. **Ingreso y Extracción de Contratos (Dual Pipeline)**
- **Creación Asistida**: Formularios dinámicos con precarga de plantillas legales.
- **Ingesta Externa y OCR**: Carga de contratos en PDF con procesamiento mediante `pdfplumber` / `PaddleOCR` para la extracción automatizada de:
  - Bloque de **VISTOS** y Decretos de respaldo.
  - Datos personales del prestador (RUT, nombre, domicilio, profesión/oficio).
  - Vigencia, montos impositivos y cuenta presupuestaria.
  - Desglose de funciones, metas y entregables por estado de pago.

### 3. **Gestión de Rúbricas y Firma de Gestión Simplificada**
- Módulo integrado en pantalla (*Signature Pad*) para captura de rúbrica sobre periféricos o pantallas táctiles.
- Inyección de metadatos de validación jurídica e inmutabilidad:
  - Identidad de la sesión activa (RUT y Nombre).
  - Estampa de tiempo exacta (Timestamp milimétrico).
  - Dirección IP de la estación de trabajo y agente del dispositivo.
  - Sello criptográfico / Hash SHA-256 del documento al momento del timbrado.

### 4. **Flujo de Aprobación de Pagos y Control Jerárquico**
- **Nivel 1 — Recepción e Ingesta Documental**: Carga del informe mensual de actividades.
- **Nivel 2 — Evaluación de Cumplimiento de Funciones**: Checklist función por función (`Cumplido`, `Parcial`, `No Cumplido`).
- **Nivel 3 — Visado Administrativo RRHH**: Auditoría de desgloses líquidos/brutos e impositivos.
- **Nivel 4 — Aprobación y Liberación de Pago**: Visto bueno final y pase a Tesorería.
- **Carril de Representación de Control**: Estado especial **`REPRESENTADO_POR_CONTROL`** para pausar legalmente expedientes observados por la Dirección de Control Interno hasta la emisión del decreto subsanatorio.

---

## Formatos y Esquema de Base de Datos

### Modelo de Base de Datos (SQLite con WAL)

#### Contrato (`Contract`)
| Campo | Tipo | Descripción | Requerido |
|-------|------|-------------|----------|
| `id` | Integer | Clave primaria | Sí |
| `provider_id` | Integer | FK a `ServiceProvider` | Sí |
| `department_id` | Integer | FK a `Department` | Sí |
| `created_by_user_id` | Integer | Trazabilidad - quién creó | No |
| `last_modified_by_user_id` | Integer | Trazabilidad - quién modificó | No |
| `contract_number` | String | Número único de contrato (ej. `CT-2026-0809`) | Sí |
| `position_title` | String | Título del cargo | Sí |
| `program_name` | String | Nombre del programa municipal | No |
| `monthly_amount_gross` | Float | Monto bruto mensual | Sí |
| `total_contract_amount` | Float | Monto total contrato | Sí |
| `start_date` | Date | Fecha inicio vigencia | Sí |
| `end_date` | Date | Fecha fin vigencia | Sí |
| `contract_date` | Date | Fecha del contrato | No |
| `budget_account` | String | Imputación presupuestaria (ej. `21.04.004`) | No |
| `sub_program` | String | Subprograma municipal | No |
| `cost_center` | String | Centro de costo | No |
| `pdf_file_path` | String | Ruta del PDF almacenado | No |
| `status` | String | Estado (`BORRADOR`, `EN_REVISION`, `FIRMADO`, `REPRESENTADO_POR_CONTROL`, `EN_EJECUCION`, `FINALIZADO`) | Sí |
| `created_at` | DateTime | Timestamp de creación | Sí |

#### Decretos Previos y Vistos (`ContractDecree`)
| Campo | Tipo | Descripción | Requerido |
|-------|------|-------------|----------|
| `id` | Integer | Clave primaria | Sí |
| `contract_id` | Integer | FK a `Contract` | Sí |
| `decree_type` | String | Tipo (`PRESUPUESTO_ANUAL`, `SUBROGANCIA`, `CONTRATO_ANTERIOR`, `FICHA_RRHH`) | Sí |
| `decree_number` | String | Identificador formal (ej. `Decreto Exento N° 3.580`) | Sí |
| `decree_date` | Date | Fecha de dictación del decreto | No |
| `description` | Text | Transcripción o glosa del Visto legal | Sí |
| `is_mandatory` | Boolean | Indica si forma parte de la plantilla anual fija | Sí |

#### Prestador (`ServiceProvider`)
| Campo | Tipo | Descripción | Requerido |
|-------|------|-------------|----------|
| `id` | Integer | Clave primaria | Sí |
| `rut` | String | RUT chileno único | Sí |
| `first_name` | String | Nombres | Sí |
| `paternal_last_name` | String | Apellido paterno | Sí |
| `maternal_last_name` | String | Apellido materno | No |
| `address` | String | Domicilio legal | No |
| `profession_or_trade` | String | Profesión u oficio | No |
| `bank_name` | String | Nombre del Banco | No |
| `account_type` | String | Tipo de cuenta bancaria | No |
| `account_number` | String | Número de cuenta | No |

#### Usuario, Roles y Permisos (`User`, `Role`, `Permission`)
| Tabla | Campo Clave | Descripción |
|-------|-------------|-------------|
| `User` | `rut_or_email`, `password_hash`, `role_id` | Gestión de identidad y acceso |
| `Role` | `name`, `receive_email_notifications` | Roles (`SUPERADMIN`, `ADMIN_RRHH`, `JEFE_DEPTO`, `FINANZAS_CONTROL`, `DIRECTOR_CONTROL`) |
| `Permission` | `code`, `description` | Permisos granulares (`contract:create`, `decree:edit`, `audit:download`, etc.) |

#### Subrogancias Temporales (`TemporarySubrogation`)
| Campo | Tipo | Descripción | Requerido |
|-------|------|-------------|----------|
| `id` | Integer | Clave primaria | Sí |
| `absent_user_id` | Integer | FK a `User` titular que se ausenta | Sí |
| `subrogate_user_id` | Integer | FK a `User` que asume la responsabilidad | Sí |
| `start_date` | Date | Fecha inicio subrogancia | Sí |
| `end_date` | Date | Fecha fin subrogancia | Sí |
| `decree_reference` | String | Número del Decreto de Subrogancia legal | Sí |

#### Bitácora de Auditoría Extendida (`AuditLog`)
| Campo | Tipo | Descripción | Requerido |
|-------|------|-------------|----------|
| `id` | Integer | Clave primaria | Sí |
| `user_id` | Integer | Usuario que ejecutó la acción | Sí |
| `action` | String | Tipo de evento (`CONTRACT_CREATE`, `DECREE_UPDATE`, `DOCUMENT_DOWNLOADED`, `DOCUMENT_PRINTED`, `SIGNATURE_STAMPED`) | Sí |
| `entity_type` | String | Tipo de entidad afectada (`contract`, `decree`, `monthly_payment`) | Sí |
| `entity_id` | Integer | ID de la entidad | Sí |
| `payload` | Text (JSON) | Metadatos extendidos (IP, User-Agent, Hash, justificaciones de reasignación) | Sí |
| `timestamp` | DateTime | Marca de tiempo inmutable | Sí |

---

## Funcionalidades y Trazabilidad Avanzada

### 1. **Auditoría de Descargas e Impresiones Físicas**
- Intercepción de rutas de backend (`GET /contracts/<id>/download-pdf`) registrando el evento `DOCUMENT_DOWNLOADED`.
- Disparador de frontend JavaScript (`navigator.sendBeacon`) que registra en `AuditLog` la acción `DOCUMENT_PRINTED` al activar impresoras locales o del sistema.
- Pestaña de historial en la interfaz Split-View para auditar en tiempo real quién ha visualizado, descargado o impreso el archivo.

### 2. **Notificaciones por Correo Configurable (Matriz RBAC)**
- Envío asíncrono de correos electrónicos para no demorar la navegación del usuario.
- Matriz de notificaciones por rol para evitar la saturación de bandejas de entrada directivas.
- Correo detallado con el resumen de la acción, responsable (RUT/Nombre) y enlace directo al expediente.

### 3. **Gestión de Cuellos de Botella y Subrogancias**
- Programación de subrogancias por período basadas en decretos alcaldicios de reemplazo.
- Reasignación rápida por parte del `ADMIN_RRHH` ante licencias médicas o ausencias imprevistas, con registro de justificación obligatoria en la bitácora de auditoría.
- Sistema de alertas con escalado automático al superior o Administrador Municipal ante estancamientos mayores a 5 días.

### 4. **Manejo Presupuestario Pasivo (Feature Flag)**
- Registro de cuentas presupuestarias y centros de costo como metadata informativa para resguardar la validez del documento.
- Arquitectura desacoplada mediante un interruptor de integración (`BUDGET_MODULE_INTEGRATION = False` por defecto) para garantizar que el sistema no altere la contabilidad oficial del municipio.

---

## Documentación de Endpoints Principales

- `GET /contracts/create` — Formulario con precarga de decretos fijos anuales.
- `POST /contracts/create` — Procesamiento y creación del expediente de contrato.
- `POST /contracts/upload` — Ingesta e interpretación OCR de PDF escaneado (sección VISTOS y contrato).
- `POST /contracts/<id>/sign` — Registro de rúbrica con estampa de metadatos (RUT, IP, Hash).
- `GET /contracts/<id>/download-pdf` — Descarga del PDF con registro automático en `AuditLog`.
- `POST /api/audit/print-event` — API para recepción de eventos de impresión física desde el cliente.
- `GET /api/search-global` — Buscador global omnipresente (`Ctrl + K`).