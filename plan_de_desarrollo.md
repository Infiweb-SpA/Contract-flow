# Plan de Desarrollo — SIGH-MUNI (Contract Flow)

> **Última actualización:** 2026-11-23
> **Documento maestro de brechas y decisiones:** `plan_brechas.md` (raíz del repo). Este plan de desarrollo se alinea con sus FASES 1–9 (§6) y su mapeo (§7).
> **Leyenda:** `[x]` = verificado como realizado en código al 2026-11-23 · `[ ]` = pendiente · `[~]` = parcial.
> **Regla de oro:** los catálogos nuevos (permisos, tipos de documento, textos fijos, etapas de visación, política de firma) nacen como **datos configurables**, no hardcodeados a Cunco, para no rehacer trabajo al llegar multi-tenant.
> **Módulo de Pagos Mensuales: ELIMINADO** (decisión 2026-11-09). Pagos vía SMC externo. No se reactiva. Limpiar referencias en docs (FASE 9).

---

## PARTE A — Registro de trabajo realizado (verificado en código)

> Hitos ya implementados. Se conservan como trazabilidad; las fases activas de la Parte B no los repiten, solo los referencian.

### A.1 Perfil de usuario (ex FASE 0)
- [x] Cambio de contraseña: `ChangePasswordForm`, `POST /auth/profile/change-password` con reautenticación, mín. 8, auditoría `USER_PASSWORD_CHANGE`. (`app/auth/routes.py`, `forms.py`)
- [x] Cambio de correo: `ChangeEmailForm`, `POST /auth/profile/change-email` con unicidad + reautenticación, auditoría `USER_EMAIL_CHANGE`.
- [x] UI `templates/auth/profile.html` con secciones de correo y contraseña.
- [ ] Verificación por correo del nuevo email → **reubicado a FASE 3.4** (hoy el cambio se aplica directo, sin verificar la nueva dirección).

### A.2 Decretos previos y VISTOS — estructura Cunco (ex FASE 1)
- [x] Tablas `contract_decrees` (instancias snapshot) + `decree_templates` (catálogo maestro anual). (`app/models/decree.py`)
- [x] Catálogo `/decrees` CRUD + activar/desactivar + filtros tipo/año (SUPERADMIN). (`app/routes/decrees.py`)
- [x] Precarga `_save_contract_decrees()`: copia plantillas activas del año como snapshot (origin PLANTILLA); editar plantilla no altera contratos existentes.
- [x] Sección VISTOS como paso del stepper (checkboxes plantillas + filas dinámicas), render en split-view y PDF.
- [x] Parser OCR `extract_decrees_vistos()`: detecta bloque VISTOS, une multilínea, descarta sellos, clasifica tipo/número/fecha (calibrado 16/16 contra escaneo real Cunco). (`app/services/ocr_service.py`)
- [x] Campos Cunco: `provider_address`, `provider_comuna`, `hours_weekly` (defecto 44), `total_amount_words` (migración `migrate_cunco_fields.py`).
- [x] Agrupación `VISTOS_TYPE_ORDER` / `order_vistos()` / tipos excluidos `BASE_LEGAL` y `CONTRATO_ACTUAL`.
- [x] `preview_template.html` jerarquía 1:1 Cunco: Hoja 1 VISTOS (cabecera institucional + base legal nacional fija Res. CGR 15.700/2012, Of. CGR 33.701/2014, Ley 18.695) → Hoja 2 DECRETO (puntos 1 APRUÉBASE / 2 contratos parte del decreto / 3 imputación Ítem + año, firmas Alcalde/Secretario, distribución) → Hoja 3+ CONTRATO (13 cláusulas).
- [x] Reactividad por año de presupuesto (`/api/decree-templates?year=`), grupo colapsable "decretos de otros años" con badge ámbar.
- [x] Split-view 3 hojas en create/edit con `updateDecretoPreview()` en tiempo real; monto en palabras auto (`numToWordsEs`).
- [x] `pdf_generator.py`: `order_vistos`, fechas español, `format_money_cl`, `number_to_words_es`, `budget_year`, logo embebido (`link_callback`).
- [x] Verificación end-to-end (PDF 6 páginas en orden correcto, logo, fechas, navegación real sin errores de consola).

### A.3 RBAC granular + notificaciones (ex FASE 2)
- [x] Modelos `Permission`, `Role`, `RolePermission`; migración `migrate_rbac_fields.py`; seed de permisos estándar (sin permisos de pago) + matriz de roles base. (`app/models/permission.py`)
- [x] Decorador `@permission_required`; bypass SUPERADMIN; protección `/admin/*`. (`app/auth/utils.py`)
- [x] Vistas SUPERADMIN: `/admin/roles` (crear/eliminar, roles base no eliminables), `/admin/roles/<rol>/assign` (matriz checkboxes), `/admin/permissions` + create. (`app/routes/admin.py`)
- [x] UI RBAC en lenguaje natural (descripción humana + chip técnico; autogenera identificador desde acción).
- [x] Gestión de usuarios/contraseñas: `/admin/users`, create, password (cambiar/generar seguro con `secrets`, mostrar una vez), toggle activo.
- [x] Visibilidad de decretos de otros años (`other_years` en API; sincronización año en `decrees/form.html`).
- [x] **Correos (Resend):** `email_service.py` (`send_email`, `send_otp_email`), config `RESEND_API_KEY/FROM_EMAIL/FROM_NAME`, modo prueba `RESEND_TEST_TO`.
- [x] **OTP:** `otp_service.py` (generar, hashear, enviar, verificar, invalidar previos, intentos máx., expiración) + modelo `VerificationCode`. (`app/services/otp_service.py`, `app/models/verification_code.py`)
- [x] **Notificaciones:** `notification_service.py` integrado en `log_action`; envía a usuarios activos con `receive_email_notifications=1` y permiso `view_audit`; catálogo `NOTIFICATION_EVENTS`.
- [x] Campo `receive_email_notifications` (migración `migrate_phase5_notifications.py`) + toggle en perfil (`/auth/profile/notifications`) y en `/admin/users`.
- [x] Plantilla de correo HTML (evento, entidad, responsable, detalles, enlace al expediente).
- [x] Suscripción granular por evento (`disabled_notifications` JSON) + UI admin `/admin/users/<id>/notification-events` (migración `migrate_phase6_notification_events.py`).
- [x] Auditoría de gestión `USER_*`, `ROLE_*`, `PERMISSION_*`.
- [ ] (Opcional) Matriz de suscripción por evento en el perfil del propio usuario → **reubicado a FASE 3.4** (hoy solo el admin la gestiona por usuario; el perfil propio tiene únicamente el toggle general).
- [ ] Confirmación en navegador por el usuario (ex 2.1bis): iniciar sesión SUPERADMIN y reiniciar Flask para ver navbar de Roles/Usuarios. *(Acción administrativa del usuario, no de código.)*

### A.4 Rúbrica / firma ágil con metadatos (ex FASE 3)
- [x] Captura de firma canvas (Signature Pad, Pointer Events: mouse/stylus/tableta/táctil) en preview y create/edit.
- [x] `POST /contracts/<id>/sign`: OTP obligatorio + metadatos inmutables (RUT, nombre, timestamp, IP, dispositivo, hash SHA-256 del documento). (`ContractSignature`)
- [x] Firma vectorial + bloque QR/código de validación al pie del PDF.

### A.5 Auditoría de descargas e impresiones (ex FASE 4)
- [x] `GET /contracts/<id>/download-pdf` registra `DOCUMENT_DOWNLOADED` (IP, archivo, timestamp).
- [x] `POST /api/audit/print-event` registra `DOCUMENT_PRINTED` (fetch/sendBeacon antes de `window.print()`).
- [x] Sección "Historial de Accesos e Impresiones" en `detail.html`.

### A.6 Firma OTP del Alcalde + activación de decretos (ex FASE 7)
- [x] **Rol base `ALCALDE`** en `BASE_ROLES` + permisos `view_contract`, `sign_contract`, `sign_decree`, `view_audit` (seed `migrate_rbac_fields.py`). *(Estaba sin marcar en el plan anterior; verificado como hecho.)*
- [x] SUPERADMIN y ALCALDE pueden firmar/activar plantillas del catálogo (permiso `sign_decree` + bypass SUPERADMIN).
- [x] Infraestructura Resend + OTP + `VerificationCode` + config (ver A.3).
- [x] `POST /contracts/<id>/sign` refactorizado con OTP; `sign-mayor` (OTP Alcalde); `sign-provider` (OTP al correo del prestador); `otp/request` por tipo de firmante; UI panel OTP en `preview_template.html`.
- [x] `POST /decrees/<id>/otp/request` + `activate` (OTP + firma Alcalde); `decrees/activate.html`; activación solo con `sign_decree`; firma del Alcalde de decretos activos se precarga en el bloque de firma del contrato.
- [~] **Bloqueo de firma del honorario sin correo:** hecho en servidor (`otp/request` y `sign-provider` rechazan si el prestador no tiene email). **Falta** marcar email como obligatorio en el modal de prestador → **reubicado a FASE 3.3**.
- [ ] Auditoría OTP (`OTP_REQUESTED/VERIFIED/FAILED`, `SIGNATURE_OTP_INVALID`, `PROVIDER_EMAIL_MISSING`) + rate limiting → **reubicado a FASE 3.3** (verificado: no implementado).

### A.7 Otros hitos verificados
- [x] Autenticación RUT/Email + contraseña (Werkzeug), sesiones, RBAC por rol. Dashboard con métricas y filtro por departamento. (`app/routes/dashboard.py`)
- [x] Buscador global omnipresente Ctrl+K en topbar → `/contracts/api/search-provider-contract`. (`templates/base.html`)
- [x] Ingesta OCR de contratos externos (`/contracts/upload`, `/api/ocr-extract`, `/api/ocr-progress`, `/api/ocr-cancel`) con creación rápida de prestador/departamento.
- [x] Renovación/clonación de contratos con nuevo correlativo e historial por funcionario (nunca sobrescribe el anterior).
- [x] Bitácora de auditoría inmutable + API de traza (`audit-trail`, `get_entity_trail`).

---

## PARTE B — Fases de desarrollo activas (alineadas con `plan_brechas.md` §6)

> Orden acordado: primero lo que se controla hoy en el piloto (permisos → antecedentes → firmas → visaciones), después la envoltura de estandarización para vender. Las FASES 1–5 se construyen sobre el código single-tenant actual y no se pierden al llegar multi-tenant.
> **Clave:** los permisos de escritura por sección (FASE 1) son el esqueleto del circuito de visaciones (FASE 5).

| Fase | Nombre | Dependencias |
|---|---|---|
| 1 | Permisos por sección + rol Secretario + numeración del decreto (+ higiene) | — |
| 2 | Antecedentes del prestador + contratación express | 1 |
| 3 | Firmas OTP unificadas + FEA complementaria + correos formales | 1 |
| 4 | Expediente pre-contractual (Requerimiento + CDP pasivo) + estados | 1, 2 |
| 5 | Circuito de visaciones configurable + subrogaciones + alertas | 1, 4 + descubrimiento |
| 6 | Fundación multi-tenant + config institucional | 1–5 |
| 7 | Motor de plantillas (ESTANDAR_CGR + CUNCO) + CONSIDERANDOS | 6 |
| 8 | SIAPER + distribución (opción SIAPER-lite tras 3) | 1, 6 |
| 9 | Endurecimiento comercial + validación jurídica + docs | todas |

---

### FASE 1 — Permisos de escritura por rol/sección + Secretario + numeración

**Objetivo:** cada rol solo escribe sus secciones (servidor + UI); el Secretario Municipal firma con OTP y es el único que numera/fecha el decreto; cerrar huecos de firma actuales.

#### 1.0 Higiene previa
- [ ] `CSRFProtect` global (Flask-WTF ya instalado, solo usado en login) + tokens en formularios y fetch POST (create/edit/sign/admin/decrees/quick-add).
- [ ] Eliminar `app/templates/contracts/pdf_template.html` (legacy Temuco hardcodeado, sin uso; el generador usa `preview_template.html`).
- [ ] Validaciones servidor en create/edit: `start_date < end_date`; `end_date ≤ 31-12` del año de inicio; montos > 0; coherencia `total ≈ mensual × meses` (advertencia); RUT chileno válido.
- [ ] Advertencia UI sobre `hours_weekly` (jornada fija = indicio de subordinación laboral; se conserva en perfil Cunco como práctica local parametrizable).

#### 1.1 Catálogo de permisos por sección + rol Secretario
- [ ] Migración idempotente (extender `migrate_rbac_fields.py` o nueva `migrate_section_permissions.py`): `write_provider_data`, `write_contract_terms`, `write_functions`, `write_vistos`, `write_budget`, `write_decree_number`, `sign_mayor`, `sign_secretary`, `sign_provider_assisted`, `change_status` (module `Contratos`).
- [ ] Rol base `SECRETARIO_MUNICIPAL` en `BASE_ROLES` (`routes/admin.py`) + seed de matriz.
- [ ] `has_permission` / `@permission_required`: el bypass de SUPERADMIN **no aplica a permisos de firma** (`sign_*`).

**Matriz rol → sección (escritura):**

| Sección | JEFE_DEPTO | ADMIN_RRHH | FINANZAS_CONTROL | ALCALDE | SECRETARIO_MUNICIPAL | AUDITOR | SUPERADMIN |
|---|---|---|---|---|---|---|---|
| Datos del prestador (personales/bancarios) | — | ✅ | — | — | — | — | ✅ |
| Condiciones del contrato (cargo, programa, fechas, montos, modalidad) | ✅ borrador | ✅ | ✅ montos | — | — | — | ✅ |
| Funciones / cometido específico | ✅ | ✅ | — | — | — | — | ✅ |
| VISTOS específicos del prestador | ✅ | ✅ | — | — | — | — | ✅ |
| Presupuesto (cuenta, subprograma, centro de costo) | — | — | ✅ | — | — | — | ✅ |
| N° y fecha del decreto | — | — | — | — | ✅ al firmar | — | — |
| Firma Alcalde | — | — | — | ✅ OTP | — | — | — |
| Firma Secretario | — | — | — | — | ✅ OTP | — | — |
| Firma prestador (asistida, OTP a su correo) | — | ✅ | — | — | — | — | — |
| Cambios de estado | — | ✅ | — | — | — | — | ✅ |

#### 1.2 Enforcement en servidor
- [ ] POST `/contracts/create` y `/<id>/edit`: whitelist de campos según permisos de la sesión; campo prohibido → ignorar/rechazar + flash + auditoría `WRITE_DENIED`.
- [ ] `sign-mayor`: restringir `@role_required` a **solo ALCALDE** (hoy acepta ADMIN_RRHH, SUPERADMIN, JEFE_DEPTO, FINANZAS_CONTROL, ALCALDE).
- [ ] `sign-provider`: operador con `sign_provider_assisted` (ADMIN_RRHH/SUPERADMIN); OTP al correo del prestador; `operator_user_id` registrado.
- [ ] Nuevo `POST /contracts/<id>/sign-secretary`: solo SECRETARIO_MUNICIPAL; OTP + rúbrica + asignación `decline_number`/`decline_date` en una transacción → estado `EMITIDO` + auditoría `DECREE_ISSUED`.
- [ ] `POST /contracts/<id>/otp/request`: nuevo purpose `CONTRACT_SIGN_SECRETARY`; restringir `signer_kind` según rol.

#### 1.3 Numeración del decreto
- [ ] `decline_number`/`decline_date` salen del formulario create/edit (solo lectura si ya existen).
- [ ] Correlativo anual sugerido (secuencia año + último número; formato configurable a futuro), editable por el Secretario.
- [ ] Estado `EMITIDO` agregado: `BORRADOR → CREADO_PARA_FIRMA → EMITIDO → INGRESADO → EN_EJECUCION → FINALIZADO` (refinamiento completo en FASE 4).

#### 1.4 Eliminación de firmas libres
- [ ] Quitar `mayor_signature`/`secretary_signature` del POST create/edit y de los modales de dibujo libre.
- [ ] Migración de datos existentes: documentos ya emitidos conservan render legacy; nuevos documentos solo vía `ContractSignature` + OTP.

#### 1.5 UI
- [ ] `can_write(section)` en contexto de create/edit/preview; secciones en solo-lectura con candado y tooltip de rol.
- [ ] Panel "Firmar y numerar decreto" exclusivo del Secretario en detail/preview.
- [ ] Modal de firma visible solo para el rol propio; navbar y admin de roles actualizados.

#### 1.6 Auditoría y tests
- [ ] Eventos `WRITE_DENIED`, `DECREE_ISSUED`, `SIGNATURE_SECRETARY` (integración `notification_service`).
- [ ] Tests pytest: matriz rol×sección (permitido/denegado), firma restringida por rol, numeración exclusiva del Secretario, CSRF activo.

**Criterios de aceptación:** cada rol solo escribe sus secciones (servidor rechaza el resto); solo ALCALDE firma como Alcalde; solo SECRETARIO_MUNICIPAL numera y firma el decreto; SUPERADMIN no firma; validaciones de fecha/monto activas; sin campos de firma dibujables libres.

---

### FASE 2 — Antecedentes del prestador + contratación express

**Objetivo:** carpeta documental por prestador con checklist y vencimientos; el modal quick-add se mantiene para express con gate de kit mínimo antes de emitir el decreto.

#### 2.1 Modelo y catálogo
- [ ] `ProviderDocument`: `provider_id`, `doc_type`, `file_path`, `original_filename`, `issue_date`, `expiry_date`, `verified_by_user_id`, `verified_at`, `status` (PENDIENTE/VERIFICADO/RECHAZADO/VENCIDO), `notes`, `created_at`.
- [ ] Catálogo `doc_types` **configurable como dato**: CEDULA, CV, ANTECEDENTES_FINES_ESPECIALES, TITULO_EXPERTO, DJ_INHABILIDADES, AFP, SALUD, SITUACION_MILITAR, OTRO.
- [ ] Requisitos por modo: **kit mínimo express** (CEDULA + DJ_INHABILIDADES + TITULO_EXPERTO) vs. carpeta completa estándar.

#### 2.2 UI Antecedentes
- [ ] Ítem navbar "Antecedentes" junto a "Crear contrato": lista de prestadores con semáforo de carpeta (completa/incompleta/vencida) + filtros.
- [ ] Vista de carpeta por prestador: upload por tipo, fechas emisión/vencimiento, verificación RRHH (VERIFICADO/RECHAZADO + observación), preview/descarga.
- [ ] Checklist de completitud en la ficha del contrato.
- [ ] Generador de **DJ de inhabilidades** prellenada (Ley 18.575) desde datos del prestador.
- [ ] Alertas de vencimiento de certificados.

#### 2.3 Contratación express
- [ ] Mantener modal quick-add (RUT, nombre, **email obligatorio para OTP**, profesión).
- [ ] Flag `carpeta_pendiente` en contrato/prestador + banner de documentos faltantes en detail.
- [ ] **Gate:** `sign-secretary` bloqueado si el kit mínimo no está VERIFICADO; mensaje claro de qué falta.
- [ ] Resto de documentos adjuntables después, con alertas de plazo configurable.
- [ ] Auditoría `PROVIDER_DOC_UPLOADED/VERIFIED/REJECTED`, `EXPRESS_FOLDER_PENDING`.

#### 2.4 Permisos
- [ ] `write_provider_documents` (ADMIN_RRHH, SUPERADMIN), `verify_provider_documents` (ADMIN_RRHH); JEFE_DEPTO lectura. Matriz actualizada.

**Criterios de aceptación:** carpeta por prestador operativa; express permite crear y firmar pero **no emitir decreto** sin kit mínimo verificado; alertas de vencimiento; DJ autogenerada.

---

### FASE 3 — Firmas OTP unificadas + FEA complementaria + correos formales

**Objetivo:** toda firma con OTP + metadatos; orden legal forzado; ingesta FEA externa como complemento; seguridad OTP; envío formal de correos con dominio verificado.
**Base ya implementada (Parte A.3/A.4/A.6):** Resend, OTP, `ContractSignature`, firma Alcalde/prestador, activación de decretos. Esta fase unifica, restringe y completa.

#### 3.1 Unificación y orden
- [ ] Toda firma (Alcalde, Secretario, prestador) vía `ContractSignature` + OTP + hash SHA-256 + metadatos (Secretario completado en FASE 1).
- [ ] **Orden forzado:** prestador → Alcalde → Secretario; los endpoints validan predecesores.
- [ ] Gates de firma configurables que se activan al existir el módulo: visaciones completas (FASE 5), CDP (FASE 4), carpeta/kit mínimo (FASE 2).

#### 3.2 FEA complementaria y política por muni
- [ ] Ruta upload/OCR existente como ingesta de documento firmado externamente (FEA): registro de hash del PDF externo + vinculación al expediente + estado `FIRMADO_EXTERNO`.
- [ ] `signature_policy` configurable: `AGIL_INTERNA` / `FEA_EXTERNA` / `HIBRIDA` (por firmante). Single-tenant como config; por tenant en FASE 6.
- [ ] Página pública de validación por código (QR) sin login: `/validar/<codigo>` → firmante, fecha, hash, estado.

#### 3.3 Seguridad OTP *(reubica pendientes 7.5 y 7.6 del plan anterior)*
- [ ] **Marcar email como obligatorio en el modal de prestador** (create/edit) + validación en `quick-add` (hoy `m_email` es opcional y el servidor acepta email vacío). *(7.5 parcial: el bloqueo de firma sin correo en servidor ya está hecho.)*
- [ ] Rate limiting OTP (por IP + por entidad) en `otp/request`.
- [ ] Auditoría OTP: `OTP_REQUESTED`, `OTP_VERIFIED`, `OTP_FAILED`, `SIGNATURE_OTP_INVALID`, `PROVIDER_EMAIL_MISSING`.
- [ ] `SECRET_KEY` sin fallback dev en producción (fail-fast si no está definida).

#### 3.4 Correos: envío formal *(reubica 0.2 y 2.2 opcional; tarea nueva de dominio)*
- [ ] **Validar dominio remitente en Resend** (DNS SPF/DKIM) y configurar `RESEND_FROM_EMAIL` definitivo (ej. `no-reply@municipalidaddecunco.cl` o dominio del producto). Hoy: config default `onboarding@resend.dev`, service default `no-reply@municipalidaddecunco.cl` sin dominio verificado. **Es lo único que falta para el envío formal de correos.**
- [ ] Desactivar `RESEND_TEST_TO` en producción (hoy redirige todos los correos a un destinatario de prueba).
- [ ] Verificación por correo del nuevo email en `change-email` (enviar código/ enlace de confirmación antes de aplicar el cambio). *(ex 0.2)*
- [ ] (Opcional) Matriz de suscripción por evento en el perfil del propio usuario. *(ex 2.2; hoy solo admin)*

**Nota legal:** OTP + rúbrica + hash + bitácora = firma electrónica **simple** con evidencia robusta (Ley 19.799), no FEA (exige certificado de prestador acreditado). La FEA externa se ingiere como complemento. Validar con Jurídica/Control de Cunco antes de ofrecerlo como "cumple lo legal" (FASE 9).

**Criterios de aceptación:** ninguna firma sin OTP; orden respetado; FEA externa ingresada y hasheada; validación pública funciona; rate limiting activo; correos salen desde dominio verificado (sin `RESEND_TEST_TO`).

---

### FASE 4 — Expediente pre-contractual (Requerimiento + CDP pasivo) + estados

**Objetivo:** cubrir la etapa 1 del flujo legal y unificar el expediente como agregado trazable.

#### 4.1 Requerimiento
- [ ] Modelo `Requerimiento`: `department_id`, `solicitado_por`, `cometido`, `perfil_requerido`, `plazo`, `monto_estimado`, `justificacion`, `estado` (SOLICITADO/AUTORIZADO/RECHAZADO), `autorizado_por`, `fecha_autorizacion`, referencia a decreto de delegación.
- [ ] UI: JEFE_DEPTO crea la solicitud; Alcalde/Administrador Municipal autoriza (delegación configurable).
- [ ] El contrato nace vinculado a un requerimiento autorizado (o express con justificación).

#### 4.2 CDP pasivo *(reubica ex FASE 5.4 — módulo presupuestario pasivo)*
- [ ] Modelo `BudgetCertificate`: `folio`, `emitido_por_unidad`, `fecha`, `monto`, `budget_account`/`subtitulo`/`item`, `programa`, `pdf_path`, `atestacion_10pct`, `estado`, vínculo a requerimiento/contrato.
- [ ] UI: FINANZAS_CONTROL registra el CDP + adjunta PDF emitido por DAF/SECPLA; atestación manual del tope 10%.
- [ ] Gate: sin CDP no se avanza a visaciones/emisión (configurable).
- [ ] Variable `BUDGET_MODULE_INTEGRATION=False` en config; `budget_account`/`cost_center` como metadata legal sin transacciones contables activas.

#### 4.3 Máquina de estados completa + expediente
- [ ] Estados: `REQUERIMIENTO → AUTORIZADO → CDP_EMITIDO → ANTECEDENTES_OK → BORRADOR → EN_VISACION → VISADO → EN_FIRMA → FIRMADO → EMITIDO → SIAPER_PENDIENTE → REGISTRADO → EN_EJECUCION → FINALIZADO`; ramas `OBSERVADO`, `REPARADO`, `TERMINADO_ANTICIPADO`.
- [ ] Transiciones validadas en servidor + auditoría; migración desde los estados actuales.
- [ ] Vista de **expediente unificado**: contrato + requerimiento + CDP + carpeta + visaciones + firmas + SIAPER.

#### 4.4 Renovación
- [ ] La clonación existente revalida CDP vigente y vencimientos de antecedentes; nuevo correlativo.

**Criterios de aceptación:** requerimiento autorizado y CDP adjunto son prerequisitos del expediente estándar; máquina de estados completa y auditada; renovación revalida antecedentes.

---

### FASE 5 — Circuito de visaciones configurable + subrogaciones + alertas

**Objetivo:** cubrir la etapa 4 del flujo legal. **Descubrimiento primero, código después** (la muni no ha explicado el flujo real).

#### 5.0 Descubrimiento (previo al código)
- [ ] Aplicar el **cuestionario de `plan_brechas.md` §8** a RRHH, Finanzas, Jurídica, Control y Secretaría de Cunco.
- [ ] Validar orden real, observaciones/reparos, delegaciones, subrogancias y plazos.

#### 5.1 Motor de visaciones
- [ ] Modelo `VisacionStage`: etapas funcionales (RRHH/FINANZAS/JURIDICA/CONTROL), orden, activa, mapeo a department/usuarios del tenant. **Configurable por datos**, flujo legal como default.
- [ ] Modelo `Visacion`: `contract_id`, `stage`, `user_id`, `accion` (VISAR/OBSERVAR/RECHAZAR), `observaciones`, `timestamp`.
- [ ] Circuito: borrador completo → `EN_VISACION` recorre etapas activas; observación devuelve al originador; rechazo termina.
- [ ] Cada etapa usa los permisos de sección de FASE 1 + acción de visado.

#### 5.2 Carril de Control Interno *(reubica ex FASE 5.3)*
- [ ] Estado `REPARADO` / `REPRESENTADO_POR_CONTROL`; Control adjunta reparos escritos; la unidad técnica sube decreto/antecedentes subsanatorios; re-visación.

#### 5.3 Subrogaciones *(reubica ex FASE 5.1)*
- [ ] `temporary_subrogations`: `absent_user_id`, `subrogate_user_id`, `start_date`, `end_date`, `decree_reference`.
- [ ] UI en perfil para programar delegaciones; **reasignación extraordinaria por RRHH** con justificación obligatoria en `AuditLog`.
- [ ] Firma del subrogante: OTP propio + metadato de subrogancia + decreto de subrogancia en VISTOS.

#### 5.4 Alertas de estancamiento *(reubica ex FASE 5.2)*
- [ ] Job periódico (cron/APScheduler) que detecta expedientes >5 días en una etapa → correo de escalamiento al superior/Administrador.
- [ ] Semáforo "días en etapa" en Ctrl+K y dashboard (verde <2, amarillo 3–5, rojo >5).

**Criterios de aceptación:** circuito configurable por muni; observaciones/reparos con subsanación; subrogaciones con decreto y OTP; alertas despachadas.

---

### FASE 6 — Fundación multi-tenant + config institucional

**Objetivo:** una BD SQLite por municipalidad; configuración institucional en BD; onboarding de nueva muni en un comando.

- [ ] Registro maestro (`master.db` o `registry.json` en volumen): slug, nombre, `db_path`, logo, activa.
- [ ] Routing por subdominio en producción; selector de municipalidad en login para dev.
- [ ] Engines SQLite por tenant + session routing por request; adaptación de app factory, auth, audit y uploads por carpeta de tenant.
- [ ] Config institucional en BD por tenant (`Municipality`): nombre, RUT, logo, comuna, jurisdicción, autoridades (Alcalde/Secretario/Administrador con delegación), `signature_policy`, `document_profile`, formatos de correlativos, lista de distribución.
- [ ] Migraciones idempotentes corren sobre cada BD de tenant; **Cunco migra a tenant #1 sin pérdida de datos**.
- [ ] Textos fijos (Fallo Tribunal Electoral 18-11-2024, Acta Concejo 06-12-2024, etc.) salen del código → catálogo por tenant/año.
- [ ] Script de onboarding: nueva muni (BD + seed + config + catálogo) en un comando.
- [ ] Tests de aislamiento (tenant A no ve datos de tenant B).

**Criterios de aceptación:** dos munis conviven aisladas; config institucional editable por UI; onboarding en un comando; Cunco intacto como tenant #1.

---

### FASE 7 — Motor de plantillas documentales

**Objetivo:** perfiles ESTANDAR_CGR (default) + CUNCO (variante); cláusulas y textos como datos; CONSIDERANDOS.

- [ ] Biblioteca de cláusulas estándar nacionales (`ClauseTemplate`) + edición por tenant.
- [ ] Perfil **ESTANDAR_CGR**: contrato bilateral separado + decreto VISTOS → **CONSIDERANDOS** → RESOLUTIVA + imputación.
- [ ] Perfil **CUNCO**: réplica actual de 3 hojas como variante (contrato integrado, testimonio en 3 ejemplares, jornada parametrizable).
- [ ] Bloque CONSIDERANDOS: dinámicos (necesidad del servicio, CDP, calidad de experto) + fijos por tenant.
- [ ] VISTOS: bases legales nacionales compartidas + catálogo local por tenant/año (extiende `decree_templates`).
- [ ] Correlativos automáticos de contrato (formato configurable); N° de decreto ya lo asigna el Secretario (FASE 1).
- [ ] Split-view y `pdf_generator` renderizan por perfil; eliminar hardcodes Cunco/Temuco restantes.

**Criterios de aceptación:** una muni nueva usa el perfil estándar sin tocar código; Cunco conserva su réplica; CONSIDERANDOS presente en el decreto estándar.

---

### FASE 8 — SIAPER + distribución

**Objetivo:** cubrir la etapa 6 del flujo legal (obligación ya citada en los VISTOS). 100% estándar nacional.

- [ ] `SiaperRegistration`: `contract_id`, `fecha_emision_decreto`, `plazo_limite` (**15 días hábiles** con feriados Chile), `estado` (PENDIENTE/ENVIADO/REGISTRADO/OBSERVADO), `responsable_user_id`, `folio_registro`, `comprobante_path`.
- [ ] El reloj arranca en `EMITIDO` (FASE 1); alertas día ~10 y vencido → escalamiento.
- [ ] Paquete de exportación: decreto + contrato firmados (+ índice de antecedentes) en ZIP/PDF para subida manual a SIAPER (**no hay API pública de CGR**).
- [ ] Distribución configurable por tenant (interesado, alcaldía, finanzas, control, oficina de partes, personal) con registro de entrega/recepción; habilitación hacia Finanzas/SMC.
- [ ] KPIs: % registrados en plazo, pendientes, vencidos.
- [ ] **Opción SIAPER-lite:** tracking + plazo sobre `decline_date` manual, adelantable tras FASE 3 como gancho comercial.

**Criterios de aceptación:** plazo de 15 días hábiles calculado y alertado; paquete exportable; distribución registrada; KPI visible.

---

### FASE 9 — Endurecimiento comercial + validación jurídica + docs

*(Reubica la ex FASE 6 "Pruebas e Integración Final".)*

- [ ] Suite pytest completa: aislamiento tenant, máquina de estados, gates, matriz de permisos, OTP, plazo SIAPER, smoke OCR.
- [ ] Probar flujo completo con el PDF escaneado de prueba de Cunco; validar que OCR diferencie VISTOS/Decreto del cuerpo del contrato.
- [ ] Verificar que las alertas por correo se despachen solo a roles suscritos.
- [ ] Asegurar que la firma ágil quede incrustada sin alterar el formato original del PDF.
- [ ] Validar registro de descargas, impresiones y subrogancias en bitácora.
- [ ] Seguridad: rate limiting global, validación de uploads (tipo/tamaño/contenido), secrets por entorno, auditoría de accesos sensibles, headers de seguridad.
- [ ] Reescritura de `README.md`, `Contextos/Requerimientos.md` y `CONTEXTO_SIGH-MUNI` alineados al producto real (eliminar referencias al módulo de pagos eliminado y a la firma "100% externalizada").
- [ ] Kit de onboarding por muni + datos demo para ventas.
- [ ] **Validación jurídica** del perfil ESTANDAR_CGR y de la política de firma OTP/FEA con la Dirección Jurídica/Control de Cunco **antes de ofrecerlo a otras munis**.

**Criterios de aceptación:** tests verdes; docs coherentes; perfil estándar y política de firma validados por el Control del piloto; nueva muni onboarded con kit.

---

## PARTE C — Mapeo de reubicación (plan anterior → este plan)

| Tarea del plan anterior | Estado | Nueva ubicación |
|---|---|---|
| 0.2 Verificación por correo del nuevo email | Pendiente | FASE 3.4 |
| 2.2 (Opcional) Matriz de eventos en perfil propio | Pendiente | FASE 3.4 |
| 7.1 Rol ALCALDE + permisos | **Hecho** (verificado) | Parte A.6 |
| 7.2 Infra Resend + OTP + config | **Hecho** (verificado) | Parte A.3 |
| 7.5 Bloqueo firma sin correo (servidor) | **Hecho** | Parte A.6 |
| 7.5 Email obligatorio en modal prestador | Pendiente | FASE 3.3 |
| 7.6 Auditoría OTP + rate limiting | Pendiente | FASE 3.3 |
| 5.1 Subrogaciones | Pendiente | FASE 5.3 |
| 5.2 Alertas estancamiento | Pendiente | FASE 5.4 |
| 5.3 Carril Control Interno | Pendiente | FASE 5.2 |
| 5.4 Presupuesto pasivo / feature flag | Pendiente | FASE 4.2 |
| FASE 6 Pruebas e integración final | Pendiente | FASE 9 |
| Módulo de Pagos Mensuales | Eliminado 2026-11-09 | No se reactiva (SMC externo) |
| **Validar dominio remitente Resend** | **Nueva** | FASE 3.4 |

---

## PARTE D — Notas técnicas y riesgos

- **Parche PaddleOCR Windows:** no remover `FLAGS_enable_pir_in_executor=0` ni `FLAGS_enable_pir_api=0` en `ocr_service.py` (crashea PaddleOCR v3.0+ en Windows).
- **SQLite:** WAL, un archivo por tenant (FASE 6), backups por volumen Railway; concurrencia limitada por tenant (asumible).
- **Legal (firma):** OTP + rúbrica es firma electrónica simple con evidencia (Ley 19.799), no FEA. Validar con Jurídica/Control antes de vender "cumple lo legal".
- **Legal (jornada):** `hours_weekly` fija es indicio de subordinación (riesgo de recalificación laboral). Parametrizar y advertir.
- **SIAPER:** sin API pública de CGR → tracking + export manual; plazo 15 días hábiles es obligación legal ya citada en los VISTOS.
- **Documentación:** fuente de verdad = `plan_brechas.md` + este plan. README/Requerimientos/Contexto deben reescribirse (FASE 9).
- **Seguridad:** CSRF global (FASE 1), rate limiting OTP (FASE 3), `SECRET_KEY` sin fallback dev (FASE 3), validación de uploads (FASE 9).
- **Correos:** todo el envío (Resend, OTP, notificaciones, suscripción granular, toggles) está operativo; solo falta **validar el dominio remitente** para el envío formal y desactivar `RESEND_TEST_TO` en producción (FASE 3.4).
