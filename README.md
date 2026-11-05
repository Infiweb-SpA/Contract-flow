# Contract-flow

**SIGH-MUNI** - Sistema Integrado de Gestión, Creación y Revisión de Honorarios Municipales

## Visión General

SIGH-MUNI es una solución SaaS integral diseñada para resolver el ciclo de vida completo de los contratos a honorarios y sus estados de pago en municipalidades de Chile. El sistema permite **armar y confeccionar nuevos contratos a honorarios** a partir de plantillas estandarizadas, así como **revisar y desglosar contratos existentes** subidos al sistema.

Dado que el proceso de firma digital se encuentra 100% externalizado en la plataforma previa y dedicada de la municipalidad, SIGH-MUNI no interviene ni valida firmas digitales, asumiendo la validez legal de los documentos firmados ingresados y concentrándose exclusivamente en:

1. La **generación/armado** de nuevos borradores y plantillas de contratos
2. La **ingesta, OCR y desglose automático de funciones y datos** (PaddleOCR / pdfplumber) para la revisión estructurada
3. El **Buscador Global Omnipresente (`Ctrl + K`)** para la localización e identificación inmediata de contratos, expedientes y pagos "en el aire"
4. El **flujo de revisión y aprobación de pagos mensuales** estructurado en las 4 etapas internas de RRHH para auditar el cumplimiento de funciones y autorizar la liberación del pago mensual

---

## Flujo del Sistema

### 1. **Ingreso y Extracción de Contratos Externos**
- Los contratos firmados se suben en formato PDF desde la plataforma externa de firma
- El motor OCR (`pdfplumber` / `PaddleOCR`) procesa el documento y extrae automáticamente:
  - Datos del prestador (RUT, nombre, profesión)
  - Vigencia y montos
  - Desglose de funciones y tareas

### 2. **Proceso de Creación de Contratos**
- **Rutas de acceso**:
  - `GET /contracts/create` - Formulario guiado de creación
  - `POST /contracts/create` - Procesamiento del contrato
  - `GET /contracts/upload` - Carga de contratos externos

- **Campos principales del formulario**:
  - **Datos del Prestador**:
    - RUT (formato chileno)
    - Nombres, Apellido Paterno, Apellido Materno
    - Domicilio, Profesión/Oficio, Nacionalidad
    - Datos bancarios (nombre banco, tipo cuenta, número)
  
  - **Datos del Contrato**:
    - Número de contrato (formato: CT-YYYY-NNNN)
    - Título del Cargo
    - Nombre del Programa Municipal
    - Monto Mensual Bruto
    - Monto Total del Contrato
    - Fecha de Inicio y Fin de Vigencia
    - Número y Fecha de Decreto de Alcaldicio
    - Tipo de Fecha (Contrato, Inicio, Término)
  
  - **Campos Administrativos (Estructura Freire)**:
    - Fecha de Contrato
    - Cuenta Presupuestaria
    - Subprograma
    - Centro de Costo
    - Modalidad de Pago (Mensual Fijo / Por Producto)
  
  - **Cláusulas de Funciones**:
    - Lista dinámica de tareas asignadas al prestador
    - Función de ordenamiento (1, 2, 3...)

### 3. **Revisión y Edición de Contratos**
- **Split-View Interface**:
  - Panel Izquierdo (40%): Visor interactivo de PDF con zoom y búsqueda
  - Panel Derecho (60%): Formulario estructurado con datos extraídos y checklist de funciones

- **Funcionalidades principales**:
  - Visualización previa (`/contracts/<id>/preview`)
  - Edición completa (`/contracts/<id>/edit`)
  - Descarga de PDF (`/contracts/<id>/download-pdf`)
  - Cambio de estado (`/contracts/<id>/change-status`)

### 4. **Flujo de Aprobación de Pagos (4 Niveles RRHH)**
1. **Nivel 1 — Recepción e Ingesta Documental**: Carga del informe mensual de actividades y verificación de concordancia con el contrato firmado
2. **Nivel 2 — Evaluación de Cumplimiento de Funciones**: Checklist ítem por ítem (`Cumplido`, `Parcial`, `No Cumplido`) de las tareas pactadas
3. **Nivel 3 — Visado Administrativo de RRHH**: Revisión de antecedentes, cálculo de honorario líquido/bruto e impositivos
4. **Nivel 4 — Aprobación y Liberación de Pago**: Emisión del visto bueno final para el envío a Finanzas/Tesorería

---

## Formatos y Campos de Datos

### Modelo de Base de Datos

#### Contrato (`Contract`)
| Campo | Tipo | Descripción | Requerido |
|-------|------|-------------|----------|
| `id` | Integer | Clave primaria | Sí |
| `provider_id` | Integer | Clave foránea a `ServiceProvider` | Sí |
| `department_id` | Integer | Clave foránea a `Department` | Sí |
| `created_by_user_id` | Integer | Trazabilidad - quién creó | No |
| `last_modified_by_user_id` | Integer | Trazabilidad - quién modificó | No |
| `contract_number` | String | Número único de contrato | Sí |
| `decline_number` | String | Número de decreto | No |
| `decline_date` | Date | Fecha de decreto | No |
| `position_title` | String | Título del cargo | Sí |
| `program_name` | String | Nombre del programa | No |
| `monthly_amount_gross` | Float | Monto bruto mensual | Sí |
| `total_contract_amount` | Float | Monto total contrato | Sí |
| `start_date` | Date | Fecha inicio vigencia | Sí |
| `end_date` | Date | Fecha fin vigencia | Sí |
| `contract_date` | Date | Fecha del contrato | No |
| `budget_account` | String | Cuenta presupuestaria | No |
| `sub_program` | String | Subprograma | No |
| `cost_center` | String | Centro de costo | No |
| `payment_modality` | String | Modalidad de pago (`MENSUAL_FIJO`, `POR_PRODUCTO`) | No |
| `pdf_file_path` | String | Ruta del PDF original | No |
| `ocr_processed` | Integer | Flag de procesamiento OCR | No |
| `status` | String | Estado (`BORRADOR`, `CREADO_PARA_FIRMA`, `INGRESADO`, `EN_EJECUCION`, `FINALIZADO`) | Sí |
| `created_at` | DateTime | Timestamps | Sí |

#### Función de Contrato (`ContractFunction`)
| Campo | Tipo | Descripción | Requerido |
|-------|------|-------------|----------|
| `id` | Integer | Clave primaria | Sí |
| `contract_id` | Integer | Clave foránea | Sí |
| `function_order` | Integer | Orden de la función | Sí |
| `function_description` | Text | Descripción detallada de la tarea | Sí |
| `created_at` | DateTime | Timestamp | Sí |

#### Prestador (`ServiceProvider`)
| Campo | Tipo | Descripción | Requerido |
|-------|------|-------------|----------|
| `id` | Integer | Clave primaria | Sí |
| `rut` | String | RUT chileno (con o sin guión) | Sí |
| `first_name` | String | Nombres | Sí |
| `paternal_last_name` | String | Apellido paterno | Sí |
| `maternal_last_name` | String | Apellido materno | No |
| `full_name` | String | Campo calculado (SQL) | - |
| `birth_date` | Date | Fecha de nacimiento | No |
| `civil_status` | String | Estado civil | No |
| `nationality` | String | Nacionalidad | No |
| `profession_or_trade` | String | Profesión u oficio | No |
| `address` | String | Domicilio | No |
| `phone` | String | Teléfono | No |
| `email` | String | Correo electrónico | No |
| `bank_name` | String | Banco | No |
| `account_type` | String | Tipo cuenta | No |
| `account_number` | String | Número cuenta | No |

#### Departamento (`Department`)
| Campo | Tipo | Descripción | Requerido |
|-------|------|-------------|----------|
| `id` | Integer | Clave primaria | Sí |
| `code` | String | Código corto (ej. DITECO) | Sí |
| `name` | String | Nombre completo | Sí |
| `cost_center` | String | Centro de costo | No |
| `is_active` | Integer | Flag activo/inactivo | No |

#### Usuario (`User`)
| Campo | Tipo | Descripción | Requerido |
|-------|------|-------------|----------|
| `id` | Integer | Clave primaria | Sí |
| `rut_or_email` | String | RUT o email para login | Sí |
| `password_hash` | String | Hash de contraseña | Sí |
| `full_name` | String | Nombre completo | Sí |
| `role` | String | Rol (`SUPERADMIN`, `ADMIN_RRHH`, `JEFE_DEPTO`, `FINANZAS_CONTROL`) | Sí |
| `department_id` | Integer | Departamento asignado | No |
| `is_active` | Integer | Flag activo/inactivo | No |

#### Bitácora de Auditoría (`AuditLog`)
| Campo | Tipo | Descripción | Requerido |
|-------|------|-------------|----------|
| `id` | Integer | Clave primaria | Sí |
| `user_id` | Integer | Usuario que realizó la acción | No |
| `action` | String | Acción (`CONTRACT_CREATE`, `CONTRACT_UPDATE`, `PAYMENT_CREATE`, etc.) | Sí |
| `entity_type` | String | Tipo de entidad (`contract`, `monthly_payment`, `service_provider`) | Sí |
| `entity_id` | Integer | ID de la entidad afectada | Sí |
| `payload` | Text | JSON con detalles específicos de la acción | No |
| `timestamp` | DateTime | Fecha y hora de la acción | Sí |

---

## Funcionalidades y Características

### 1. **Sistema de Autenticación y Autorización por Roles**
- **Roles disponibles**:
  - `SUPERADMIN`: Administración completa del sistema
  - `ADMIN_RRHH`: Creación de contratos, carga externa, gestión de usuarios
  - `JEFE_DEPTO`: Creación de requerimientos, revisión de funciones, aprobación mensual
  - `FINANZAS_CONTROL`: Aprobación final de pagos y liberaciones
- **Mecanismo de login**:
  - Autenticación por RUT o correo electrónico
  - Hash de contraseñas con werkzeug
  - Session management seguro

### 2. **Motor OCR y Extracción de Datos**
- **Procesadores duales**:
  - `pdfplumber` para PDFs nativos
  - `PaddleOCR` para PDFs escaneados
- **Extracción automática**:
  - RUT del prestador
  - Nombres y apellidos
  - Profesión y nacionalidad
  - Departamento/Unidad
  - Montos y vigencia
  - Desglose de funciones y tareas
- **Tiempo de procesamiento objetivo**: < 4.5 segundos

### 3. **Buscador Global Omnipresente (`Ctrl + K`)
- **Criterios de búsqueda**:
  - RUT (con o sin puntos/guión)
  - Nombres, Apellidos
  - Número de contrato (ej. `CT-2026-0809`)
  - Número de Decreto Alcaldicio
  - Departamento/Unidad origen
  - Estado del flujo de trabajo
- **Visualización de resultados**:
  - Ubicación exacta en el sistema
  - Alerta trazable de tiempo de estancamiento
  - Indicadores visuales de estado (verde: < 2 días, amarillo: 3-5 días, rojo: > 5 días)

### 4. **Interfaz Split-View**
- **Panel Izquierdo (40% ancho)**:
  - Visor interactivo de PDF con zoom y búsqueda interna
  - Navegación rápida entre páginas
  - Selección de texto y copiado

- **Panel Derecho (60% ancho)**:
  - Formulario estructurado de datos extraídos
  - Checklist de funciones con estados: `Cumplido`, `Parcial`, `No Cumplido`
  - Cuadro de observaciones por función
  - Botones de acción rápida: `[Aprobar]`, `[Observar]`, `[Rechazar]`

### 5. **Métricas y KPIs Operativos**
- **Dashboard principal**:
  - Contratos Activos
  - Pagos Pendientes en Mi Nivel
  - Expedientes Detenidos (+5 días)
  - Pagos Aprobados del Mes

- **Filtros rápidos**:
  - Por Departamento
  - Por Estado del Contrato
  - Por Rol de usuario

### 6. **Gestión de Versiones y Trazabilidad**
- **Tracking completo**:
  - Creación/modificación de contratos
  - Aprobación/rechazo de pagos
  - Cambios de estado de workflow
  - Creación automática de prestadores/departamentos vía OCR
- **API de auditoría**:
  - `get_contract_audit_trail()` - Historial completo de contrato y pagos relacionados
  - `get_entity_trail()` - Historial específico de cualquier entidad
- **Datos almacenados en bitácora**:
  - Usuario que realizó la acción
  - Timestamp exacto
  - Payload JSON con detalles

---

## Flujo de Trabajo Detallado

### Paso 1: Creación de Contrato (Ruta Admin RRHH)
1. **Acceder a** `/contracts/create`
2. **Completar formulario**:
   - Seleccionar o buscar prestador existente
   - Seleccionar departamento solicitante
   - Ingresar datos contractuales
   - Agregar funciones y cláusulas
3. **Validación**:
   - Verificar RUT del prestador
   - Validar formatos de fechas
   - Confirmar montos
4. **Procesamiento**:
   - Guardar en base de datos SQLite
   - Generar trazabilidad en audit_logs
   - Redirigir a vista previa del contrato

### Paso 2: Ingesta de Contrato Externo (Ruta Admin RRHH)
1. **Acceder a** `/contracts/upload`
2. **Subir PDF**:
   - Seleccionar archivo PDF firmado
   - Completar campos manuales (número, posición, monto)
   - Procesamiento asíncrono con OCR
3. **Extracción OCR**:
   - Extraer texto del PDF
   - Parsear datos con regex y ML
   - Matchear con base de datos de prestadores/departamentos
   - Auto-crear entidades si no existen
4. **Revisión**:
   - Validar datos extraídos
   - Corregir errores si es necesario
   - Guardar contrato en estado `INGRESADO`

### Paso 3: Ciclo de Aprobación de Pagos
1. **Nivel 1 - Jefe de Departamento**:
   - Recibir notificación de nuevo contrato/pago
   - Cargar informe mensual de actividades
   - Verificar concordancia con contrato firmado
   - Pasar a Nivel 2 o devolver observaciones

2. **Nivel 2 - Revisión de Funciones**:
   - Revisar checklist de cumplimiento por función
   - Marcar cada función como:
     - `Cumplido` = ✅
     - `Parcial` = ⚠️
     - `No Cumplido` = ❌
   - Agregar observaciones específicas
   - Visar y pasar a Nivel 3

3. **Nivel 3 - Visado Administrativo RRHH**:
   - Revisar cálculos de honorarios
   - Verificar impuestos y descuentos
   - Validar documentación soporte
   - Aprobar o observar cálculo

4. **Nivel 4 - Finanzas/Control**:
   - Aprobación final del desembolso
   - Liberación de pago a prestador
   - Generación de documentos de liquidación
   - Cierre del expediente

---

## Configuración Técnica

### Entorno de Desarrollo
- **Backend**: Python 3.11 + Flask (Arquitectura modular con Blueprints)
- **Base de Datos**: SQLite (con modo WAL habilitado)
- **Frontend**: Tailwind CSS + Vanilla JS / Alpine.js
- **OCR**: PaddleOCR (`PP-OCRv4` / `es`) + `pdfplumber` + `pdf2image`
- **Despliegue**: Railway (contenerizado SaaS)

### Configuraciones de Base de Datos
```sql
-- Tablas principales
CREATE TABLE contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id INTEGER NOT NULL,
    department_id INTEGER NOT NULL,
    created_by_user_id INTEGER,
    last_modified_by_user_id INTEGER,
    contract_number VARCHAR(50) UNIQUE NOT NULL,
    -- ... otros campos
);

CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INTEGER NOT NULL,
    payload TEXT,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### Configuraciones de APIs
- **API de Extracción OCR**: `POST /api/ocr-extract` (con cancelación)
- **API de Progreso**: `GET /api/ocr-progress` (polling)
- **API de Cancelación**: `POST /api/ocr-cancel`
- **API de Búsqueda**: `GET /api/search-provider`, `GET /api/search-provider-contract`

---

## Seguridad y Confiabilidad

### 1. **Seguridad de Datos**
- **Autenticación**: Hash de contraseñas con werkzeug
- **Autorización**: Control por roles (RBAC)
- **Cifrado**: TLS para todas las comunicaciones
- **Validación**: Validación estricta de entradas de formularios

### 2. **Confiabilidad del Sistema**
- **Procesamiento OCR asíncrono**: Con cancelación por token
- **Registros de actividad**: Todos los cambios auditados e inmutables
- **Soporte multiusuario**: Sesiones concurrency-safe
- **Almacenamiento persistente**: Volúmenes Railway para SQLite y PDFs

### 3. **Mantenimiento y Monitoreo**
- **Alertas de estancamiento**: Detección automática de retrasos > 5 días
- **KPIs operativos**: Métricas en tiempo real
- **Logs detallados**: Trazabilidad completa de todas las acciones

---

## Documentación de APIs y Endpoints

### Rutas del Sistema

#### Rutas de Contratos (`/contracts/`)
- `GET /contracts/create` - Formulario de creación
- `POST /contracts/create` - Procesar nuevo contrato
- `GET /contracts/<id>` - Ver detalles del contrato
- `GET /contracts/<id>/edit` - Formulario de edición
- `POST /contracts/<id>/edit` - Procesar edición
- `GET /contracts/<id>/preview` - Vista previa HTML
- `GET /contracts/<id>/download-pdf` - Descargar PDF
- `POST /contracts/<id>/change-status` - Cambiar estado
- `GET /contracts/upload` - Formulario de carga externa
- `POST /contracts/upload` - Procesar carga externa

#### APIs Auxiliares
- `GET /api/search-provider?q=<query>` - Búsqueda dinámica de prestadores
- `GET /api/provider/<id>/detail` - Obtener detalles de prestador
- `POST /provider/quick-add` - Agregar prestador rápidamente
- `POST /department/quick-add` - Agregar departamento rápidamente
- `GET /api/preview` - Generar vista previa en tiempo real

---

## Guías de Uso

### Para Administradores RRHH
1. **Crear nuevo contrato**:
   - Usar `/contracts/create` para armar borradores
   - Completar todos los campos requeridos
   - Agregar cláusulas de funciones detalladas
   - Exportar a PDF para revisión

2. **Cargar contrato firmado**:
   - Usar `/contracts/upload` para PDFs externos
   - Permitir procesamiento OCR automático
   - Revisar datos extraídos
   - Corregir errores si es necesario

3. **Monitorear estado**:
   - Usar dashboard para KPIs operativos
   - Revisar bandeja de pagos pendientes
   - Gestionar alertas de estancamiento

### Para Jefes de Departamento
1. **Revisar contratos asignados**:
   - Usar bandeja `/dashboard/`
   - Filtrar por departamento propio
   - Revisar contratos en estado `CREADO_PARA_FIRMA`

2. **Validar cumplimiento de funciones**:
   - Usar Split-View para revisar PDF e checklist
   - Evaluar cada función como `Cumplido`/`Parcial`/`No Cumplido`
   - Agregar observaciones específicas

3. **Aprobar primer nivel**:
   - Pasar a Nivel 3 Visado Administrativo RRHH
   - Documentar justificación de aprobaciones

### Para Finanzas/Control
1. **Aprobación final**:
   - Usar dashboard con filtro `FINANZAS_CONTROL`
   - Revisar todos los pagos `APROBADO_RRHH`
   - Realizar aprobación final y liberación de pago

2. **Reportes y métricas**:
   - Generar reportes mensuales de pagos
   - Analizar tendencias de aprobación
   - Monitorear cumplimiento de plazos

---

## Notas de Implementación

### Estrategia de Extracción OCR
- **Dual approach**: pdfplumber para PDFs nativos, PaddleOCR para escaneados
- **Procesamiento robusto**: Manejo de diferentes formatos de documentos
- **Time optimization**: Procesamiento asíncrono con reportes de progreso
- **Match algorithms**: Fuzzy matching para RUT y nombres de prestadores/departamentos

### Arquitectura y Diseño
- **Modular Flask**: Blueprints para separación de preocupaciones
- **Frontend responsivo**: Tailwind CSS para dispositivos móviles
- **Split-View UI**: Maximizar productividad con pantalla dividida
- **Buscador global**: Navegación instantánea desde cualquier módulo

### Escalable y Mantenible
- **Base de datos SQLite**: Cero dependencias externas, despliegues instantáneos
- **Prácticas de archivo**: Uso de plantillas reutilizables
- **Documentación**: Comandos claros y bien documentados
- **Testing**: Pruebas unitarias para servicios críticos

---

## Acerca de SIGH-MUNI

**SIGH-MUNI** (Sistema Integrado de Gestión, Creación y Revisión de Honorarios Municipales) es una solución integral para municipalidades de Chile que simplifica el ciclo de vida completo de los contratos a honorarios. Desde la creación inicial hasta la aprobación final de pagos, SIGH-MUNI estandariza procesos, mejora la trazabilidad y reduce el tiempo administrativo.

**Características principales**:
- ⚡ **Aceleración de procesos**: Automatización de tareas manuales repetitivas
- 🔍 **Visibilidad total**: Buscador global con trazabilidad en tiempo real
- 📊 **Métricas operativas**: Dashboard de KPIs para toma de decisiones
- 🛡️ **Cumplimiento**: Estructuras estandarizadas que siguen regulaciones chilenas
- 🔧 **Configurable**: Parametrizable según necesidades específicas de cada municipalidad

**Este proyecto prototipo** demuestra las funcionalidades principales del sistema SIGH-MUNI completo, sentando las bases para futuras expansiones y mejoras.
