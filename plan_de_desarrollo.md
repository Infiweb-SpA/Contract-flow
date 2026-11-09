# Plan de Implementación de Funcionalidades y Trazabilidad Avanzada — SIGH-MUNI (ContractFlow)

Este documento detalla las tareas de desarrollo necesarias para extender y adaptar la plataforma **SIGH-MUNI** a los requerimientos normativos, operativos y de trazabilidad exigidos por la municipalidad (SECPLA/Control).

---

## FASE 1: Rediseño del Módulo de Decretos Previos y Vistos Buenos

### 1.1 Extensión de la Base de Datos para Decretos
- [x] Crear la tabla `contract_decrees` en SQLite (instancias por contrato) junto a `decree_templates` (catálogo maestro), con la siguiente estructura:
  - `id`: INTEGER PRIMARY KEY
  - `contract_id`: INTEGER (FK a `contracts`, cascade delete)
  - `template_id`: INTEGER FK (trazabilidad de la plantilla de origen)
  - `decree_type`: STRING (`PRESUPUESTO_ANUAL`, `CONTRATO_ANTERIOR`, `CONTRATO_ACTUAL`, `FICHA_RRHH`, `PROGRAMA_MUNICIPAL`, `SUBROGANCIA_ALCALDE`, `SUBROGANCIA_CONTROL`, `BASE_LEGAL`, `ANTECEDENTE_INSTITUCIONAL`, `OTRO`)
  - `decree_number`: STRING (ej. `Decreto Exento N° 3.580`)
  - `decree_date`: DATE
  - `description`: TEXT (Texto completo del visto/antecedente)
  - `origin`: STRING (`PLANTILLA` snapshot del catálogo | `MANUAL` ingreso del usuario)
  - `display_order`, `created_at`
- [x] Tabla `decree_templates`: plantillas fijas del año (`decree_type`, `decree_number`, `decree_date`, `description`, `year`, `is_active`, `created_at`)

### 1.2 Catálogo Maestro de Decretos Anuales Estandarizados
- [x] Vista de administración `/decrees` (CRUD + activar/desactivar + filtros por tipo/año), exclusiva para `SUPERADMIN`.
- [x] Servicio de precarga: `_save_contract_decrees()` copia las plantillas activas del año como snapshot (origin PLANTILLA) al crear/editar contratos; edición posterior de plantillas no altera contratos existentes.

### 1.3 Integración en Formulario y Split-View (`GET /contracts/create` & `/edit`)
- [x] Sección **"Decretos y Antecedentes Previos (VISTOS)"** como Paso 4 del stepper, con checkboxes de plantillas fijas y filas dinámicas para decretos específicos del prestador.
- [x] Bloque VISTOS renderizado en la hoja A4 del panel derecho (vista previa en vivo) y en el PDF oficial (`preview_template.html`).
- [x] Parser OCR `extract_decrees_vistos()` en `/api/ocr-extract` y `/contracts/upload`: detecta el bloque VISTOS, une ítems multilínea, descarta sellos/timbres del scanner y clasifica tipo/número/fecha automáticamente. Calibrado contra el contrato escaneado real de la Municipalidad de Cunco (16/16 ítems extraídos correctamente).

### 1.4 Refinamiento estructural "Cunco" (página 1 VISTOS + página 2 DECRETO)
- [x] Nuevas columnas en `contracts` (migración idempotente `migrate_cunco_fields.py`): `provider_address`, `provider_comuna`, `hours_weekly` (defecto 44), `total_amount_words`.
- [x] OCR ampliado (sección 4b): extrae domicilio del prestador, comuna y jornada semanal ("con una jornada de N horas") del contrato escaneado; el autofill no pisa campos editados manualmente (flag `dataset.manual`).
- [x] Agrupación VISTOS/DECRETO en `models/decree.py`: `VISTOS_TYPE_ORDER` (orden canónico, OTRO al final), `order_vistos()`, tipos excluidos `BASE_LEGAL` (inyectado fijo en plantilla) y `CONTRATO_ACTUAL` (objeto del punto 1 del DECRETO). El tipo `OTRO` se conserva en VISTOS para no perder antecedentes ya cargados.
- [x] `preview_template.html` con jerarquía 1:1 del decreto de Cunco:
  - Página 1: bloque VISTOS con cabecera institucional fija (Fallo Tribunal Electoral 18-11-2024 + Acta Concejo 06-12-2024) + decretos dinámicos por `decree_type` + base legal nacional fija (Resolución CGR 15.700/2012, Oficio CGR 33.701/2014, Ley 18.695/1988).
  - Página 2 (nueva, tras salto de página): **Decreto Alcaldicio N° {decline_number}** con REF, línea "DECRETO" y puntos 1 (APRUÉBASE dinámico: contrato, prestador con domicilio/comuna, programa, cargo, monto formateado y en letras, fechas y jornada semanal), 2 (fijo: contratos forman parte del decreto) y 3 (imputación al Ítem {budget_account} del Presupuesto Municipal año {budget_year}), remate "Anótese, tómese razón y comuníquese." y bloque de firma del Alcalde.
- [x] Paso 4: textos institucionales fijos NO son seleccionables en el catálogo; `decree_templates` reacciona al año de presupuesto (`/api/decree-templates?year=YYYY` + JS en create/edit que recarga plantillas al cambiar `start_date` y conserva las marcadas de otro año con la etiqueta "(año distinto del vigente)").
- [x] Formulario: campos nuevos — domicilio y comuna del prestador (Paso 1, precargados desde la ficha vía `/api/provider/<id>/detail`), jornada semanal (defecto 44) y monto total en palabras auto-generado (`numToWordsEs`, editable) — integrados en create y edit, con relleno por OCR y vista previa en vivo.
- [x] `pdf_generator.py`: helper `order_vistos`, fechas en español, `format_money_cl`, `number_to_words_es` (fallback), `budget_year` (año de `start_date`), `hours_weekly` (defecto 44), `total_amount_formatted`.
- [x] Prueba de integración (temporal, eliminada tras ejecutar): 38 verificaciones OK — orden VISTOS, exclusión BASE_LEGAL/CONTRATO_ACTUAL, disminución del catálogo por año, preview HTML y `api/preview` con página 2 completa, PDF generado y RBAC `/decrees`.

### 1.5 Réplica visual 1:1 del documento de prueba en la vista en vivo + PDF (hojas 1/2/3+)
- [x] Reestructuración del orden según el PDF escaneado real (verificado página por página con OCR): **Hoja 1 = DECRETO (VISTOS) → Hoja 2 = DECRETO (puntos resolutivos) → Hoja 3+ = CONTRATO**.
- [x] `create.html` y `edit.html`: panel A4 del split-view ahora muestra las 3 hojas completas (3× `paper-sheet`), mismas tablas y orden que el borrador/PDF. `updateDecretoPreview()` actualiza en tiempo real el encabezado del decreto (N°/REF/fecha, ambas hojas), punto 1 (fecha, nombre/RUT/domicilio/comuna del prestador, programa, monto formateado + palabras, vigencia desde-al, jornada semanal) y punto 3 (ítem + año de presupuesto); conectada en `updatePreview()` (debounce) y en la inicialización.
- [x] VISTOS en Hoja 1 con ítem autogenerado "El Contrato a Prestación de Servicios de fecha … suscrito entre la {municipalidad} y don(ña) {prestador}" (ítem 13 del decreto real) + constantes JS `MUNI_NAME`/`MUNI_CITY` derivadas de la config.
- [x] Hoja 2: "Anótese, comuníquese, regístrese y archívese.", firmas (Secretario Municipal izquierda en blanco + Alcalde derecha con nombre/RUT) y pie "DISTRIBUCIÓN: Interesado / Alcaldía / Archivo Dirección de Finanzas / Archivo Dirección de Control Interno / Oficina de Partes / Archivo de Personal". En Hoja 2 y borrador NO se repite el membrete completo (solo el encabezado del decreto), igual que el documento real → evita desbordar a una 4ª página.
- [x] Hoja del contrato: comparecencia "En la comuna de {muni_city}", firma única del Alcalde y testimonio en tres ejemplares (el prestador no firma), datos de la municipalidad desde `g.*` (config).
- [x] `pdf_generator.py`: `link_callback` para xhtml2pdf (resuelve `/static/logos_muni/...` → embebe el logo municipal en el PDF descargado).
- [x] Verificación end-to-end ejecutada (scripts temporales, ya eliminados): GET `/contracts/create`(200), `/contracts/{id}/edit`(200) y `/contracts/{id}/preview`(200) con las 39 marcas de las 3 hojas presentes; `api/preview` 200; PDF descargado de 6 páginas en orden correcto (1 VISTOS / 2 DECRETO completo con firmas+distribución / 3-6 contrato), logo embebido y fechas en español; navegación real en navegador (login → create → edit) con el panel en vivo poblado desde los datos del contrato y reactividad confirmada (nº decreto, fechas e ítem presupuestario reflejados al instante), sin errores de consola.

---

**NOTA GENERAL (2026-11-09):** El módulo de Pagos Mensuales (bandejas, revisión/aprobación, payments) fue **eliminado del proyecto** por decisión del usuario — no es requisito. Las referencias a pagos en fases posteriores de este plan quedan sin efecto; los permisos `approve_payment_lvl1/lvl2` fueron removidos del catálogo RBAC.

---

## FASE 2: Gestión Fina de Permisos (RBAC) y Notificaciones por Correo

### 2.1 Módulo de Gestión de Roles y Permisos Granulares
- [x] Crear modelos `Permission` y `RolePermission` para soportar asignación fina de permisos.
  - `app/models/permission.py`: `Permission` (permiso granular con `name`/`description`/`module`), `Role` (nombre de rol disponible; NO reemplaza al campo string `User.role`, lo complementa), `RolePermission` (asignación rol→permiso, unique por par).
  - Migración idempotente `migrate_rbac_fields.py`: crea tablas `roles`, `permissions` y `role_permissions`; seed de 10 permisos estándar (create/edit/view/delete_contract, create/edit/delete_decree, manage_users, manage_roles, view_audit — sin permisos de pago: el módulo de Pagos fue eliminado del proyecto a solicitud del usuario) y matriz inicial rol→permiso para los 5 roles base (SUPERADMIN, ADMIN_RRHH, JEFE_DEPTO, FINANZAS_CONTROL, AUDITOR).
- [x] Crear vista de administración exclusiva para el `SUPERADMIN` que permita:
  - Crear y editar roles personalizados. → `/admin/roles` (listado con etiqueta BASE, crear rol, eliminar rol — roles base del sistema no eliminables, y refuse si hay usuarios asignados), `/admin/roles/create`. Los roles persisten en la tabla `roles` (`is_base=1` para los del sistema).
  - Asignar permisos específicos (ej. `create_contract`, `edit_decree`, `approve_payment_lvl1`, etc.). → `/admin/roles/{rol}/assign` (matriz de checkboxes por permiso, guarda y reporta), `/admin/permissions` + `/admin/permissions/create` para gestionar el catálogo de permisos.
  - Decorador `@permission_required('permiso')` en `app/auth/utils.py`: verifica que el rol del usuario en sesión tenga el permiso; `SUPERADMIN` siempre pasa (bypass). Protección de `/admin/*` con `@role_required('SUPERADMIN')` y enlace "Roles y Permisos" en el navbar solo visible para SUPERADMIN.
  - Prueba de integración (temporal, eliminada tras ejecutar): 22 verificaciones OK — seed, RBAC de la vista, CRUD de roles/permisos, y decorador (permitir a rol con permiso, bloquear sin él, bypass SUPERADMIN).
  - Nota: las rutas existentes (`/contracts/*`, `/payments/*`) conservan sus `@role_required`; el acople de `@permission_required` por ruta se hará junto con la planificación de la lógica de aprobación de decretos/contratos acordada con el usuario.
- [x] UI del RBAC en lenguaje natural (para usuarios no técnicos):
  - `assign_permissions.html`: checklist agrupado por módulo (Contratos / Decretos / Usuarios / Auditoría / General) — cada permiso muestra la descripción humana como etiqueta principal y el identificador técnico como chip secundario en monospace.
  - `permissions.html` en formato "Acción permitida" con área del sistema; `create_permission.html` pide la acción en lenguaje natural y autogenera el identificador técnico (JS, soporta vocales tildadas).
  - `roles.html`: chips de permisos con descripción + fuente técnica, botón a "Usuarios y Contraseñas", nota de que los cambios se aplican de inmediato.
- [x] Gestión de usuarios y contraseñas (solo SUPERADMIN):
  - `/admin/users` (listado + crear usuario con rol, departamento y contraseña), `/admin/users/create`, `/admin/users/{id}/password` (cambiar o generar nueva contraseña; mín. 8 caracteres si es manual; se muestra UNA sola vez con botón Copiar y opción "Generar otra"), `/admin/users/{id}/toggle` (activar/desactivar).
  - Enlace "Usuarios" en el navbar para SUPERADMIN; generación segura con `secrets` (alfabeto sin caracteres ambíguos).
- [x] Visibilidad de decretos de otros años en contratos (bug reportado por usuario: decreto de año 2023 no aparecía):
  - `/contracts/api/decree-templates` devuelve además `other_years` (plantillas activas de otros años del catálogo).
  - `create.html`/`edit.html`: grupo colapsable "Decretos de otros años del catálogo" con badge ámbar "Año N", desmarcados por defecto.
  - `decrees/form.html`: el select "Año de Vigencia" se sincroniza automáticamente con el año de la fecha del decreto (JS) — evita decretos con año desfasado como el detectado (2023/2026).
  - Prueba de integración (temporal, eliminada tras ejecutar): 38 verificaciones OK — usuarios/contraseñas (crear, mín. 8, generar, cambiar, login con nueva, toggle), RBAC amigable, API de otros años, plantillas estáticas.

### 2.1bis Pendiente de confirmación en navegador (usuario)
- Usuario debe iniciar sesión como SUPERADMIN (`super@muni.cl` / `super123`) y reiniciar su Flask (`python app.py`) para ver "Roles y Permisos" y "Usuarios" en el navbar, la gestión de usuarios, el checklist amigable de permisos, y los decretos de otros años en el Paso 2 de contratos.

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