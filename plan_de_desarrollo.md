# Plan de Implementación de Funcionalidades y Trazabilidad Avanzada — SIGH-MUNI (ContractFlow)

Este documento detalla las tareas de desarrollo necesarias para extender y adaptar la plataforma **SIGH-MUNI** a los requerimientos normativos, operativos y de trazabilidad exigidos por la municipalidad (SECPLA/Control).

---

## FASE 1: Rediseño del Módulo de Decretos Previos y Vistos Buenos

### 1.1 Extensión de la Base de Datos para Decretos
- [ ] Crear la tabla `preliminary_decrees` o `contract_decrees` en SQLite con la siguiente estructura:
  - `id`: INTEGER PRIMARY KEY
  - `contract_id`: INTEGER (FK a `contracts`)
  - `decree_type`: STRING (ej. `PRESUPUESTO_ANUAL`, `CONTRATO_ANTERIOR`, `FICHA_RRHH`, `PROGRAMA_MUNICIPAL`)
  - `decree_number`: STRING (ej. `Decreto Exento N° 3.580`)
  - `decree_date`: DATE
  - `description`: TEXT (Texto completo del visto/antecedente)
  - `is_mandatory`: BOOLEAN (Flag para decretos estandarizados del año)
  - `created_at`: DATETIME

### 1.2 Catálogo Maestro de Decretos Anuales Estandarizados
- [ ] Implementar vista de administración para gestionar la **Plantilla Anual de Decretos Municipales** (Presupuesto vigente, desgloses, decretos de subrogancia de Alcalde y Dirección de Control).
- [ ] Crear servicio en Flask que precargue automáticamente estos decretos fijos en cualquier borrador de contrato nuevo.

### 1.3 Integración en Formulario y Split-View (`GET /contracts/create` & `/edit`)
- [ ] Incorporar la sección **"Decretos y Antecedentes Previos (VISTOS)"** en el panel derecho del formulario.
- [ ] Habilitar controles para:
  - Seleccionar decretos fijos del año mediante checkboxes.
  - Añadir de forma dinámica decretos/fichas específicas del prestador.
- [ ] Actualizar el parser OCR (`pdfplumber` / `PaddleOCR`) en `/contracts/upload` para reconocer y extraer automáticamente el bloque de **VISTOS** del contrato escaneado.

---

## FASE 2: Gestión Fina de Permisos (RBAC) y Notificaciones por Correo

### 2.1 Módulo de Gestión de Roles y Permisos Granulares
- [ ] Crear modelos `Permission` y `RolePermission` para soportar asignación fina de permisos.
- [ ] Crear vista de administración exclusiva para el `SUPERADMIN` que permita:
  - Crear y editar roles personalizados.
  - Asignar permisos específicos (ej. `create_contract`, `edit_decree`, `approve_payment_lvl1`, etc.).

### 2.2 Matriz y Configuración de Notificaciones por Correo
- [ ] Añadir campo `receive_email_notifications` (BOOLEAN) y matriz de suscripción de eventos en la configuración del rol/usuario.
- [ ] Implementar servicio de envío de correos asíncrono (usando Flask-Mail o ejecutor en segundo plano) para evitar bloqueos en el UI.
- [ ] Configurar plantillas de correo HTML informativas que incluyan:
  - Evento realizado (ej. "Modificación de Decretos", "Firma Registrada").
  - Identificación del responsable (Nombre, RUT, Rol).
  - Enlace directo al expediente en ContractFlow.

---

## FASE 3: Módulo de Rúbrica / Firma Ágil con Metadatos de Validación

### 3.1 Interfaz de Captura de Firma Frontend
- [ ] Integrar biblioteca JavaScript de firma digital (ej. *Signature Pad*) en la vista de edición y previsualización (`/contracts/<id>/preview`).
- [ ] Adaptar la interfaz para capturar rúbricas mediante periféricos USB (tabletas Wacom, pantallas táctiles, mouse o stylus).

### 3.2 Servicio Backend de Sellado y Metadatos
- [ ] Diseñar el endpoint `POST /contracts/<id>/sign` para procesar la firma digital interna.
- [ ] Almacenar los metadatos inmutables de la firma:
  - RUT y Nombre de la sesión activa del firmante.
  - Timestamp exacto con precisión de milisegundos.
  - Dirección IP de la estación de trabajo y tipo de dispositivo.
  - Hash SHA-256 del contenido del documento al momento de firmar.
- [ ] Estampar dinámicamente la firma vectorial + bloque de código QR/texto de validación al pie de las páginas del PDF.

---

## FASE 4: Auditoría de Descargas e Impresiones en Bitácora (`AuditLog`)

### 4.1 Captura de Eventos Backend (Descarga PDF)
- [ ] Interceptar la ruta `GET /contracts/<id>/download-pdf`.
- [ ] Registrar automáticamente en `AuditLog` un evento con:
  - `action`: `DOCUMENT_DOWNLOADED`
  - `user_id`: ID del usuario en sesión
  - `payload`: JSON con IP, nombre de archivo y marca de tiempo.

### 4.2 Captura de Eventos Frontend (Impresión Local)
- [ ] Interceptar las llamadas al botón de impresión o `window.print()` en la interfaz visual.
- [ ] Enviar una petición silenciosa mediante `fetch` o `navigator.sendBeacon` al endpoint `POST /api/audit/print-event` antes de desplegar el cuadro de diálogo de impresión.
- [ ] Registrar en `AuditLog` la acción `DOCUMENT_PRINTED` con la misma estructura de metadatos.

### 4.3 Visualización del Historial en el Expediente
- [ ] Añadir una pestaña **"Historial de Accesos e Impresiones"** en la interfaz Split-View del contrato para mostrar en tiempo real la lista de usuarios que han visualizado, descargado o impreso el documento.

---

## FASE 5: Subrogancias, Control de Estancamiento y Estados Institucionales

### 5.1 Módulo de Subrogancias Temporales
- [ ] Crear la tabla `temporary_subrogations` (`id`, `absent_user_id`, `subrogate_user_id`, `start_date`, `end_date`, `decree_reference`).
- [ ] Crear interfaz en el perfil de usuario para programar delegaciones de firmas y aprobaciones durante ausencias/vacaciones.
- [ ] Implementar vista de **Reasignación Extraordinaria por RRHH** para transferir la bandeja de un usuario ausente sin subrogante designado, registrando la justificación obligatoria en `AuditLog`.

### 5.2 Sistema de Alertas y Escalamiento por Estancamiento
- [ ] Programar tarea periódica (*cron job* o tarea en segundo plano) que analice contratos y pagos detenidos por más de 5 días en un mismo nivel.
- [ ] Disparar correos de alerta de escalamiento automático al Administrador Municipal o superior jerárquico según el rol.

### 5.3 Carril Legal de Representación por Control Interno
- [ ] Añadir el estado `REPRESENTADO_POR_CONTROL` al flujo de vida del contrato.
- [ ] Habilitar en el UI la opción para que la Dirección de Control adjunte observaciones escritas (Reparos) y la unidad técnica pueda subir el decreto o antecedentes subsanatorios.

### 5.4 Módulo Presupuestario Pasivo (Feature Flag)
- [ ] Crear la variable de configuración global `BUDGET_MODULE_INTEGRATION = False` en `config.py`.
- [ ] Asegurar que los campos `budget_account` y `cost_center` actúen como metadata de referencia legal sin ejecutar bloqueos o transacciones contables activas.

---

## FASE 6: Pruebas e Integración Final

- [ ] Probar el flujo completo con el PDF escaneado de prueba de la Municipalidad de Cunco.
- [ ] Validar que la extracción OCR diferencie correctamente los Vistos/Decretos del cuerpo del contrato.
- [ ] Verificar que las alertas por correo se despachen únicamente a los roles suscritos.
- [ ] Asegurar que la firma ágil quede incrustada de forma clara sin alterar el formato original del PDF.
- [ ] Validar el registro de descargas, impresiones físicas y subrogancias en la bitácora de auditoría.