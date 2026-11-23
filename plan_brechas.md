# PLAN DE BRECHAS Y DESARROLLO — SIGH-MUNI (Contract Flow)

> **Fecha:** 2026-11-23
> **Estado:** Aprobado en conversación (decisiones confirmadas por el usuario)
> **Propósito:** Documento maestro de brechas y ruta de desarrollo. **A partir de este plan se deben crear y/o modificar las tareas de `plan_de_desarrollo.md`** (ver mapeo en §7).
> **Piloto:** Ilustre Municipalidad de Cunco · **Objetivo:** producto SaaS estandarizado para todas las municipalidades de Chile.
> **Fuente de verdad del código:** `muni-sigh-app/app` + `plan_de_desarrollo.md`. El `README.md`, `Contextos/Requerimientos.md` y `CONTEXTO_SIGH-MUNI` están desincronizados (describen un módulo de pagos eliminado el 2026-11-09 y firma "100% externalizada" que ya no aplica).

---

## 1. Contexto y objetivo

El proyecto nació como **creación de contratos**; luego se agregó el módulo de **decretos** tras presentar el piloto, y los requisitos siguieron creciendo. Para dejar de crecer por parches, se ancló el alcance al **flujo legal real y nacional** de contratación a honorarios municipales, con el objetivo de **estandarizar el producto para ofrecerlo a todas las munis**, no solo Cunco.

**Tesis del producto:** *motor legal nacional estándar + capa de configuración por municipalidad*. Sin esa capa, cada muni nueva es un fork del código (como ocurrió con Cunco y Freire) y el SaaS es inmanteinible.

### 1.1 Marco legal de referencia
- Ley N° 18.883, art. 4 (honorarios: expertos, labor accidental/no habitual, plazo máx. 31-12, tope 10% del gasto en personal de planta).
- Ley N° 18.695 (Orgánica Constitucional de Municipalidades).
- Ley N° 18.575 (inhabilidades e incompatibilidades administrativas).
- Ley N° 19.880 (Bases de Procedimiento Administrativo).
- Ley N° 19.799 (Firma Electrónica).
- Resolución CGR N° 15.700/2012 y Oficio CGR N° 33.701/2014 (**registro SIAPER obligatorio**, 15 días hábiles). Ya citadas en los VISTOS del sistema.
- Dictamen CGR N° E173171 (referencia del flujo levantado por el usuario).

### 1.2 Flujo legal estándar (6 etapas)
1. **Requerimiento y validación presupuestaria**: solicitud de la unidad requirente → autorización Alcalde/Administrador Municipal → Certificado de Disponibilidad Presupuestaria (CDP) con imputación Subtítulo 21 (ítem 03 gestión interna / ítem 04 asignación 004 programas) y control del tope 10%.
2. **Antecedentes del prestador**: cédula, CV, certificado de antecedentes para fines especiales, título/acreditación de experto, DJ de inhabilidades, situación militar, AFP/salud, datos bancarios.
3. **Redacción de contrato y decreto**: contrato bilateral (sin subordinación laboral) + decreto alcaldicio (VISTOS → CONSIDERANDOS → RESOLUTIVA + imputación).
4. **Visaciones internas**: RRHH → Finanzas (DAF) → Jurídica → Control Interno.
5. **Firma y suscripción**: prestador firma **solo el contrato** → Alcalde firma contrato y decreto → Secretario Municipal firma como ministro de fe, **numera y fecha el decreto**.
6. **SIAPER y distribución**: registro electrónico en 15 días hábiles + distribución de copias (requirente, Finanzas, RRHH, etc.).

---

## 2. Estado actual verificado (código al 2026-11-23)

| Área | Estado | Evidencia |
|---|---|---|
| Armador stepper + split-view en vivo (3 hojas: VISTOS / DECRETO / CONTRATO, réplica Cunco) | ✅ | `routes/contract_builder.py`, `templates/contracts/create.html`, `edit.html` |
| Contrato 13 cláusulas (naturaleza jurídica sin relación laboral, funciones, informe, terminación anticipada, etc.) | ✅ | `templates/contracts/preview_template.html` |
| Catálogo anual de decretos VISTOS con snapshot por contrato, filtro por año, activación con firma OTP del Alcalde | ✅ | `models/decree.py`, `routes/decrees.py` |
| OCR PaddleOCR + pdfplumber calibrado contra escaneo real Cunco (VISTOS 16/16) | ✅ | `services/ocr_service.py`, `/api/ocr-extract`, `/contracts/upload` |
| Firma ágil: canvas + OTP (Resend) + hash SHA-256 + IP/dispositivo + QR/código de validación (Alcalde y prestador) | ✅ | `models/contract.py` (`ContractSignature`), `sign-mayor`, `sign-provider`, `services/otp_service.py` |
| RBAC granular (roles base + personalizados, permisos, gestión de usuarios); rol ALCALDE ya existe | ✅ | `models/permission.py`, `routes/admin.py` (`BASE_ROLES`) |
| Auditoría + notificaciones por correo + eventos descarga/impresión | ✅ | `services/audit_service.py`, `notification_service.py`, `/api/audit/print-event` |
| Buscador global Ctrl+K · renovación/clonación | ✅ | `templates/base.html`, `/api/search-provider-contract` |
| Estados `BORRADOR → CREADO_PARA_FIRMA → INGRESADO → EN_EJECUCION → FINALIZADO` (cambio manual ADMIN_RRHH) | ⚠️ lineal | `change-status` |
| Módulo de pagos mensuales | ❌ eliminado (2026-11-09) | Pagos vía SMC externo; no se reactiva |

### 2.1 Huecos concretos detectados en el código
- `sign-mayor` acepta `ADMIN_RRHH, SUPERADMIN, JEFE_DEPTO, FINANZAS_CONTROL, ALCALDE` → **cualquiera de esos roles puede ejecutar la firma del Alcalde**. Debe ser solo ALCALDE.
- `mayor_signature` / `secretary_signature` se dibujan libremente en create/edit **sin OTP, sin rol, sin validación** (paralelo a `ContractSignature`).
- `decline_number` / `decline_date` se digitan manualmente **al crear** el contrato (legalmente los asigna el Secretario al final).
- **Sin CSRF**: Flask-WTF instalado pero solo usado en login; todos los POST de contratos/admin usan `request.form` sin token.
- Sin validaciones legales: `end_date ≤ 31-12`, `start < end`, montos > 0, coherencia total.
- `pdf_template.html` legacy con **Temuco hardcodeado** (sin uso; el generador usa `preview_template.html`). Eliminar.
- Textos institucionales de Cunco hardcodeados como "fijos" (Fallo Tribunal Electoral 18-11-2024, Acta Concejo 06-12-2024) en JS de create/edit y plantilla.
- `hours_weekly` defecto 44 (práctica Cunco; jornada fija = indicio de subordinación laboral, riesgo legal).
- Config institucional single-tenant por variables de entorno (`config.py`).
- Sin suite de tests automatizados (las pruebas del plan fueron scripts temporales eliminados).
- Pendientes del plan actual: 7.5 (email prestador obligatorio), 7.6 (auditoría OTP + rate limiting), FASE 5 completa (subrogaciones, alertas, carril Control, presupuesto pasivo), FASE 6 (pruebas).

---

## 3. Brechas por etapa del flujo legal

| Etapa | Cobertura | Brecha principal |
|---|---|---|
| 1. Requerimiento + CDP | 🔴 inexistente | No hay entidad requerimiento, ni autorización de autoridad, ni CDP; `budget_account` es texto libre; sin validación 31-12 ni tope 10% |
| 2. Antecedentes del prestador | 🔴 inexistente | Solo datos personales/bancarios en `ServiceProvider`; sin carpeta documental, sin checklist, sin vencimientos, sin acreditación de experto |
| 3. Contrato + decreto | 🟡 fuerte | Falta bloque **CONSIDERANDOS**; N° decreto manual al crear; sin correlativos automáticos; `hours_weekly` riesgoso; template legacy Temuco |
| 4. Visaciones internas | 🔴 inexistente | Sin circuito RRHH→DAF→Jurídica→Control; cambio de estado manual lineal; roles FINANZAS_CONTROL/AUDITOR sin función de visación |
| 5. Firma y suscripción | 🟡 avanzado | Dos mecanismos de firma sin conciliar; sin rol Secretario ni ministro de fe; sin orden forzado ni gates; naturaleza legal OTP (simple) vs FEA sin definir |
| 6. SIAPER + distribución | 🔴 inexistente | Sin tracking de registro, sin plazo 15 días hábiles, sin alertas, sin paquete de exportación, distribución solo texto estático |

**Transversales:** falta concepto de **Expediente** (agregado requerimiento+CDP+carpeta+contrato+decreto+visaciones+firmas+SIAPER); máquina de estados insuficiente; alertas de estancamiento y subrogaciones pendientes; sin alertas de vencimiento/renovación masiva; multi-municipalidad no soportada; documentación desincronizada; seguridad (CSRF, rate limiting, SECRET_KEY dev fallback).

---

## 4. Estándar nacional vs. variación local

### 4.1 Estándar nacional (motor del producto, igual para todas las munis)
Flujo de 6 etapas · base legal (§1.1) · obligación SIAPER (15 días hábiles) · carpeta mínima de antecedentes · estructura del decreto (VISTOS/CONSIDERANDOS/RESOLUTIVA + imputación Subtítulo 21) · cláusulas mínimas del contrato · reglas de firma (prestador solo contrato; Alcalde ambos; Secretario numera/fecha) · correlativos y validaciones de plazo.

### 4.2 Variación local (hoy hardcodeado → configuración por municipalidad)

| Elemento local | Dónde está hoy | Debe ser |
|---|---|---|
| Textos institucionales (Fallo Tribunal Electoral 18-11-2024, Acta Concejo 06-12-2024) | Constantes en `create.html`/`edit.html` y `preview_template.html` | Catálogo de textos fijos **por tenant/año** |
| Estructura "Cunco" (3 hojas, contrato integrado al decreto, 3 ejemplares, jornada 44) | Plantilla única + JS split-view | **Perfiles de documento** (ESTANDAR_CGR / CUNCO) |
| Datos institucionales y del Alcalde | `config.py` por env (single-tenant) | Entidad `Municipality` en BD + UI admin |
| Jurisdicción "Temuco", membrete, distribución | `pdf_template.html` legacy + pie fijo | Config por tenant; eliminar legacy |
| Nombres de unidades (DIDECO, SECPLA, DAF, Control…) | Roles implícitos | **Etapas funcionales** mapeadas a unidades/usuarios locales |
| Formatos de numeración (Decreto Exento N° X, CT-YYYY-NNNN) | Digitación manual | Correlativos automáticos con formato configurable |

---

## 5. Decisiones de arquitectura confirmadas (2026-11-23)

| # | Decisión | Acuerdo |
|---|---|---|
| 1 | Multi-tenancy | **Una BD SQLite por municipalidad** en volumen Railway (registro maestro + routing por subdominio; selector en login para dev). Aislamiento fuerte, backup por cliente, respeta regla SQLite exclusivo |
| 2 | CDP / presupuesto | **CDP pasivo**: entidad con folio, monto, cuenta, PDF adjunto y atestación manual del tope 10%. Gate de presencia para avanzar. `BUDGET_MODULE_INTEGRATION=False` se mantiene |
| 3 | Política de firma | **OTP integrado para todas las firmas** + ingesta del PDF firmado externamente con FEA como complemento. Configurable por muni (ÁGIL / FEA / HÍBRIDA). Validación jurídica con Jurídica/Control del piloto |
| 4 | Perfiles documentales | **ESTANDAR_CGR (default) + CUNCO (variante)**. Freire se migra después si hay demanda |
| 5 | Gate contratación express | Se crea y firma con carpeta incompleta; **el Secretario no puede numerar/emitir decreto** sin kit mínimo verificado (cédula + DJ inhabilidades + acreditación experto). Resto se adjunta después con alertas |
| 6 | SUPERADMIN y firmas | Gestiona todo, **no firma en nombre de otros**. Cada firma exige sesión del rol real + OTP (excepción: prestador asistido con OTP a su correo y `operator_user_id` registrado) |
| 7 | Creación de borradores | **JEFE_DEPTO y ADMIN_RRHH crean**, cada uno escribe solo sus secciones según matriz |

---

## 6. Ruta de desarrollo (orden acordado con el usuario)

> Orden: primero lo que se controla hoy en el piloto (permisos → antecedentes → firmas → visaciones), después la envoltura de estandarización para vender. Las FASES 1–5 se construyen sobre el código single-tenant actual y **no se pierden** al llegar multi-tenant (la BD por muni replica el mismo esquema), siempre que los catálogos nuevos nazcan como **datos configurables**, no hardcodeados a Cunco.
>
> **Clave:** los permisos de escritura por sección (FASE 1) son el **esqueleto del circuito de visaciones** (FASE 5). Cuando la muni explique el flujo real, el circuito solo orquesta en secuencia esos mismos permisos.

| Fase | Nombre | Dependencias |
|---|---|---|
| 1 | Permisos por sección + rol Secretario + numeración del decreto (+ higiene) | — |
| 2 | Antecedentes del prestador + contratación express | 1 |
| 3 | Firmas OTP unificadas + FEA complementaria + orden | 1 |
| 4 | Expediente pre-contractual (Requerimiento + CDP pasivo) + máquina de estados | 1, 2 |
| 5 | Circuito de visaciones configurable + subrogaciones + alertas | 1, 4 + descubrimiento con muni |
| 6 | Fundación multi-tenant + config institucional | 1–5 (catálogos como datos) |
| 7 | Motor de plantillas (ESTANDAR_CGR + CUNCO) + CONSIDERANDOS | 6 |
| 8 | SIAPER + distribución (opción SIAPER-lite adelantable tras 3) | 1 (EMITIDO), 6 |
| 9 | Endurecimiento comercial + validación jurídica + docs | todas |

---

### FASE 1 — Permisos de escritura por rol/sección + Secretario + numeración

**Objetivo:** cada rol solo puede escribir sus secciones del contrato (servidor + UI); el Secretario Municipal firma con OTP y es el único que numera/fecha el decreto; se cierran los huecos de firma actuales.

#### 1.0 Higiene previa
- [ ] `CSRFProtect` global (Flask-WTF ya instalado) + tokens en formularios y fetch POST (create/edit/sign/admin/decrees/quick-add).
- [ ] Eliminar `app/templates/contracts/pdf_template.html` (legacy Temuco, sin uso).
- [ ] Validaciones servidor en create/edit: `start_date < end_date`; `end_date ≤ 31-12` del año de `start_date`; montos > 0; coherencia `total ≈ mensual × meses` (advertencia si difiere); RUT chileno válido.
- [ ] Advertencia UI sobre `hours_weekly` (jornada fija = indicio de subordinación; se conserva en perfil Cunco como práctica local parametrizable).

#### 1.1 Catálogo de permisos por sección + rol Secretario
- [ ] Migración idempotente (extender `migrate_rbac_fields.py` o nueva `migrate_section_permissions.py`) con permisos: `write_provider_data`, `write_contract_terms`, `write_functions`, `write_vistos`, `write_budget`, `write_decree_number`, `sign_mayor`, `sign_secretary`, `sign_provider_assisted`, `change_status` (module `Contratos`).
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
- [ ] `sign-mayor`: restringir `@role_required` a **solo ALCALDE** (hoy acepta 5 roles).
- [ ] `sign-provider`: operador con `sign_provider_assisted` (ADMIN_RRHH/SUPERADMIN); OTP al correo del prestador; `operator_user_id` registrado.
- [ ] Nuevo `POST /contracts/<id>/sign-secretary`: solo SECRETARIO_MUNICIPAL; OTP + rúbrica + asignación de `decline_number`/`decline_date` en una transacción → estado `EMITIDO` + auditoría `DECREE_ISSUED`.
- [ ] `POST /contracts/<id>/otp/request`: nuevo purpose `CONTRACT_SIGN_SECRETARY`.

#### 1.3 Numeración del decreto
- [ ] `decline_number`/`decline_date` salen del formulario create/edit (solo lectura si ya existen).
- [ ] Correlativo anual sugerido (secuencia año + último número; formato configurable a futuro), editable por el Secretario.
- [ ] Estado `EMITIDO` agregado a la máquina: `BORRADOR → CREADO_PARA_FIRMA → EMITIDO → INGRESADO → EN_EJECUCION → FINALIZADO` (refinamiento completo en FASE 4).

#### 1.4 Eliminación de firmas libres
- [ ] Quitar `mayor_signature`/`secretary_signature` del POST create/edit y de los modales de dibujo libre.
- [ ] Migración de datos existentes: documentos ya emitidos conservan render legacy; nuevos documentos solo vía `ContractSignature` + OTP.

#### 1.5 UI
- [ ] `can_write(section)` en contexto de create/edit/preview; secciones en solo-lectura con candado y tooltip de rol.
- [ ] Panel "Firmar y numerar decreto" exclusivo del Secretario en detail/preview.
- [ ] Modal de firma visible solo para el rol propio; navbar y admin de roles actualizados.

#### 1.6 Auditoría y tests
- [ ] Eventos `WRITE_DENIED`, `DECREE_ISSUED`, `SIGNATURE_SECRETARY`, `OTP_*` (integración `notification_service`).
- [ ] Tests pytest: matriz rol×sección (permitido/denegado), firma restringida por rol, numeración exclusiva del Secretario, CSRF activo.

**Criterios de aceptación:** cada rol solo escribe sus secciones (servidor rechaza el resto); solo ALCALDE firma como Alcalde; solo SECRETARIO_MUNICIPAL numera y firma el decreto; SUPERADMIN no firma; validaciones de fecha/monto activas; sin campos de firma dibujables libres.

---

### FASE 2 — Antecedentes del prestador + contratación express

**Objetivo:** carpeta documental por prestador con checklist y vencimientos; el modal quick-add se mantiene para contratación express con gate de kit mínimo antes de emitir el decreto.

#### 2.1 Modelo y catálogo
- [ ] `ProviderDocument`: `provider_id`, `doc_type`, `file_path`, `original_filename`, `issue_date`, `expiry_date`, `verified_by_user_id`, `verified_at`, `status` (PENDIENTE/VERIFICADO/RECHAZADO/VENCIDO), `notes`, `created_at`.
- [ ] Catálogo `doc_types` **configurable como dato** (tabla o JSON seed): CEDULA, CV, ANTECEDENTES_FINES_ESPECIALES, TITULO_EXPERTO, DJ_INHABILIDADES, AFP, SALUD, SITUACION_MILITAR, OTRO.
- [ ] Requisitos por modo: **kit mínimo express** (CEDULA + DJ_INHABILIDADES + TITULO_EXPERTO) vs. carpeta completa estándar.

#### 2.2 UI Antecedentes
- [ ] Ítem navbar "Antecedentes" junto a "Crear contrato": lista de prestadores con semáforo de carpeta (completa/incompleta/vencida) + filtros.
- [ ] Vista de carpeta por prestador: upload por tipo, fechas emisión/vencimiento, verificación RRHH (VERIFICADO/RECHAZADO + observación), preview/descarga.
- [ ] Checklist de completitud en la ficha del contrato (documentos del prestador vinculados).
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

**Criterios de aceptación:** carpeta por prestador operativa; express permite crear y firmar pero **no emitir decreto** sin kit mínimo verificado; alertas de vencimiento funcionan; DJ autogenerada.

---

### FASE 3 — Gobernanza de firmas OTP unificada + FEA complementaria

**Objetivo:** toda firma con OTP + metadatos inmutables; orden legal forzado; ingesta de FEA externa como complemento; seguridad OTP.

#### 3.1 Unificación y orden
- [ ] Toda firma (Alcalde, Secretario, prestador) vía `ContractSignature` + OTP + hash SHA-256 + metadatos (infra existente; Secretario completado en FASE 1).
- [ ] **Orden forzado:** prestador → Alcalde → Secretario; los endpoints validan predecesores.
- [ ] Gates de firma configurables que se activan al existir el módulo correspondiente: visaciones completas (FASE 5), CDP (FASE 4), carpeta/kit mínimo (FASE 2).

#### 3.2 FEA complementaria y política por muni
- [ ] Ruta upload/OCR existente como ingesta de documento firmado externamente (FEA): registro de hash del PDF externo + vinculación al expediente + estado `FIRMADO_EXTERNO`.
- [ ] `signature_policy` configurable: `AGIL_INTERNA` / `FEA_EXTERNA` / `HIBRIDA` (por firmante). En single-tenant como config; por tenant en FASE 6.
- [ ] Página pública de validación por código (QR) sin login: `/validar/<codigo>` → firmante, fecha, hash, estado.

#### 3.3 Seguridad OTP (pendientes 7.5/7.6 del plan actual)
- [ ] Email del prestador obligatorio + validación en quick-add y modal.
- [ ] Rate limiting OTP (por IP + por entidad); auditoría `OTP_REQUESTED/VERIFIED/FAILED`, `SIGNATURE_OTP_INVALID`, `PROVIDER_EMAIL_MISSING`.
- [ ] `SECRET_KEY` sin fallback dev en producción (fail-fast si no está definida).

**Nota legal:** OTP + rúbrica + hash + bitácora = **firma electrónica simple con evidencia robusta** (Ley 19.799), no FEA (que exige certificado de prestador acreditado). La FEA externa se ingiere como complemento. Validar con Jurídica/Control de Cunco antes de ofrecerlo como "cumple lo legal" (FASE 9).

**Criterios de aceptación:** ninguna firma sin OTP; orden respetado; FEA externa ingresada y hasheada; validación pública funciona; rate limiting activo.

---

### FASE 4 — Expediente pre-contractual (Requerimiento + CDP pasivo) + estados

**Objetivo:** cubrir la etapa 1 del flujo legal y unificar el expediente como agregado trazable.

#### 4.1 Requerimiento
- [ ] Modelo `Requerimiento`: `department_id`, `solicitado_por`, `cometido`, `perfil_requerido`, `plazo`, `monto_estimado`, `justificacion`, `estado` (SOLICITADO/AUTORIZADO/RECHAZADO), `autorizado_por`, `fecha_autorizacion`, referencia a decreto de delegación.
- [ ] UI: JEFE_DEPTO crea la solicitud; Alcalde/Administrador Municipal autoriza (delegación configurable).
- [ ] El contrato nace vinculado a un requerimiento autorizado (o express con justificación).

#### 4.2 CDP pasivo
- [ ] Modelo `BudgetCertificate`: `folio`, `emitido_por_unidad`, `fecha`, `monto`, `budget_account`/`subtitulo`/`item`, `programa`, `pdf_path`, `atestacion_10pct`, `estado`, vínculo a requerimiento/contrato.
- [ ] UI: FINANZAS_CONTROL registra el CDP + adjunta PDF emitido por DAF/SECPLA; atestación manual del tope 10%.
- [ ] Gate: sin CDP no se avanza a visaciones/emisión (configurable). `BUDGET_MODULE_INTEGRATION=False` se mantiene (módulo pasivo, sin transacciones contables).

#### 4.3 Máquina de estados completa + expediente
- [ ] Estados: `REQUERIMIENTO → AUTORIZADO → CDP_EMITIDO → ANTECEDENTES_OK → BORRADOR → EN_VISACION → VISADO → EN_FIRMA → FIRMADO → EMITIDO → SIAPER_PENDIENTE → REGISTRADO → EN_EJECUCION → FINALIZADO`; ramas `OBSERVADO`, `REPARADO`, `TERMINADO_ANTICIPADO`.
- [ ] Transiciones validadas en servidor + auditoría; migración desde los estados actuales.
- [ ] Vista de **expediente unificado**: contrato + requerimiento + CDP + carpeta + visaciones + firmas + SIAPER.

#### 4.4 Renovación
- [ ] La clonación existente revalida CDP vigente y vencimientos de antecedentes; nuevo correlativo.

**Criterios de aceptación:** requerimiento autorizado y CDP adjunto son prerequisitos del expediente estándar; máquina de estados completa con transiciones auditadas; renovación revalida antecedentes.

---

### FASE 5 — Circuito de visaciones configurable + subrogaciones + alertas

**Objetivo:** cubrir la etapa 4 del flujo legal. **Es un problema de descubrimiento primero, de código después** (la muni no ha explicado el flujo real).

#### 5.0 Descubrimiento (previo al código)
- [ ] Aplicar el **cuestionario de §8** a RRHH, Finanzas, Jurídica, Control y Secretaría de Cunco.
- [ ] Validar orden real, observaciones/reparos, delegaciones, subrogancias y plazos.

#### 5.1 Motor de visaciones
- [ ] Modelo `VisacionStage`: etapas funcionales (RRHH/FINANZAS/JURIDICA/CONTROL), orden, activa, mapeo a department/usuarios del tenant. **Configurable por datos**, con el flujo legal como default.
- [ ] Modelo `Visacion`: `contract_id`, `stage`, `user_id`, `accion` (VISAR/OBSERVAR/RECHAZAR), `observaciones`, `timestamp`.
- [ ] Circuito: borrador completo → `EN_VISACION` recorre etapas activas; observación devuelve al originador para corrección; rechazo termina.
- [ ] Cada etapa usa los permisos de sección de FASE 1 + acción de visado.

#### 5.2 Carril de Control Interno (FASE 5.3 del plan actual)
- [ ] Estado `REPARADO` / `REPRESENTADO_POR_CONTROL`; Control adjunta reparos escritos; la unidad técnica sube decreto/antecedentes subsanatorios; re-visación.

#### 5.3 Subrogaciones (FASE 5.1 del plan actual)
- [ ] `temporary_subrogations`: `absent_user_id`, `subrogate_user_id`, `start_date`, `end_date`, `decree_reference`.
- [ ] UI en perfil para programar delegaciones; **reasignación extraordinaria por RRHH** con justificación obligatoria en `AuditLog`.
- [ ] Firma del subrogante: OTP propio + metadato de subrogancia + decreto de subrogancia en VISTOS.

#### 5.4 Alertas de estancamiento (FASE 5.2 del plan actual)
- [ ] Job periódico (cron/APScheduler) que detecta expedientes >5 días en una etapa → correo de escalamiento al superior/Administrador.
- [ ] Semáforo "días en etapa" en Ctrl+K y dashboard (verde <2, amarillo 3–5, rojo >5).

**Criterios de aceptación:** circuito configurable por muni; observaciones/reparos con subsanación; subrogaciones con decreto y OTP; alertas de estancamiento despachadas.

---

### FASE 6 — Fundación multi-tenant + config institucional

**Objetivo:** una BD SQLite por municipalidad; configuración institucional en BD; onboarding de nueva muni en un comando.

- [ ] Registro maestro (`master.db` o `registry.json` en volumen): slug, nombre, `db_path`, logo, activa.
- [ ] Routing por subdominio en producción; selector de municipalidad en login para dev.
- [ ] Engines SQLite por tenant + session routing por request; adaptación de app factory, auth, audit y uploads por carpeta de tenant.
- [ ] Config institucional en BD por tenant (`Municipality`): nombre, RUT, logo, comuna, jurisdicción, autoridades (Alcalde/Secretario/Administrador con delegación), `signature_policy`, `document_profile`, formatos de correlativos, lista de distribución.
- [ ] Migraciones idempotentes corren sobre cada BD de tenant; **Cunco migra a tenant #1 sin pérdida de datos**.
- [ ] Textos fijos (Fallo Tribunal Electoral, Acta Concejo, etc.) salen del código → catálogo por tenant/año.
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

- [ ] `SiaperRegistration`: `contract_id`, `fecha_emision_decreto`, `plazo_limite` (cómputo de **15 días hábiles** con feriados Chile), `estado` (PENDIENTE/ENVIADO/REGISTRADO/OBSERVADO), `responsable_user_id`, `folio_registro`, `comprobante_path`.
- [ ] El reloj arranca en `EMITIDO` (FASE 1); alertas día ~10 y vencido → escalamiento.
- [ ] Paquete de exportación: decreto + contrato firmados (+ índice de antecedentes) en ZIP/PDF para subida manual a SIAPER (**no hay API pública de CGR**).
- [ ] Distribución configurable por tenant (interesado, alcaldía, finanzas, control, oficina de partes, personal) con registro de entrega/recepción; habilitación hacia Finanzas/SMC.
- [ ] KPIs: % registrados en plazo, pendientes, vencidos.
- [ ] **Opción SIAPER-lite:** tracking + plazo sobre `decline_date` manual, adelantable tras FASE 3 como gancho comercial.

**Criterios de aceptación:** plazo de 15 días hábiles calculado y alertado; paquete exportable; distribución registrada; KPI visible.

---

### FASE 9 — Endurecimiento comercial + validación jurídica

- [ ] Suite pytest completa: aislamiento tenant, máquina de estados, gates, matriz de permisos, OTP, plazo SIAPER, smoke OCR.
- [ ] Seguridad: rate limiting global, validación de uploads (tipo/tamaño/contenido), secrets por entorno, auditoría de accesos sensibles, headers de seguridad.
- [ ] Reescritura de `README.md`, `Contextos/Requerimientos.md` y `CONTEXTO_SIGH-MUNI` alineados al producto real (eliminar referencias al módulo de pagos eliminado y a la firma "100% externalizada").
- [ ] Kit de onboarding por muni + datos demo para ventas.
- [ ] **Validación jurídica** del perfil ESTANDAR_CGR y de la política de firma OTP/FEA con la Dirección Jurídica/Control de Cunco **antes de ofrecerlo a otras munis**.
- [ ] `plan_de_desarrollo.md` actualizado desde este documento (mapeo §7).

**Criterios de aceptación:** tests verdes; docs coherentes; perfil estándar y política de firma validados por el Control del piloto; nueva muni onboarded con kit.

---

## 7. Relación con `plan_de_desarrollo.md` (mapeo de tareas)

| Fase del plan actual | Estado | Destino en este plan |
|---|---|---|
| FASE 0 (perfil: correo/contraseña) | ✅ hecha | Se mantiene; verificación de email nuevo se activa con Resend (FASE 3) |
| FASE 7 (OTP + rol ALCALDE) | Parcial | 7.1 rol ALCALDE ya existe; 7.3/7.4 hechas → se refactorizan en FASE 1/3 (restricción de roles, unificación); **7.5/7.6 pendientes → FASE 3** |
| FASE 1 (decretos/VISTOS Cunco) | ✅ hecha | Se generaliza en **FASE 7** (motor de plantillas, CONSIDERANDOS, perfiles) |
| FASE 2 (RBAC + notificaciones) | ✅ hecha | Se extiende en **FASE 1** (permisos por sección) y **FASE 6** (config por tenant) |
| FASE 3 (rúbrica + metadatos) | ✅ hecha | Se unifica en **FASE 3** de este plan |
| FASE 4 (auditoría descargas/impresiones) | ✅ hecha | Se mantiene |
| FASE 5.1 (subrogaciones) | Pendiente | → **FASE 5.3** |
| FASE 5.2 (alertas estancamiento) | Pendiente | → **FASE 5.4** |
| FASE 5.3 (carril Control) | Pendiente | → **FASE 5.2** |
| FASE 5.4 (presupuesto pasivo / feature flag) | Pendiente | → **FASE 4.2** (CDP pasivo) |
| FASE 6 (pruebas finales) | Pendiente | → **FASE 9** |
| Módulo de pagos mensuales | ❌ eliminado 2026-11-09 | No se reactiva; pagos vía SMC externo. Limpiar referencias en docs (FASE 9) |

**Tareas nuevas a crear en `plan_de_desarrollo.md`:** todas las de FASES 1–9 de este documento que no existan (permisos por sección, rol Secretario, numeración al firmar, antecedentes/express, unificación OTP/FEA, requerimiento/CDP, expediente/estados, visaciones, multi-tenant, motor de plantillas, SIAPER, endurecimiento).

---

## 8. Cuestionario de descubrimiento del circuito real (para la muni)

> Aplicar a RRHH/Gestión de Personas, Finanzas (DAF), SECPLA, Jurídica, Control Interno, Secretaría Municipal y Alcaldía. Las respuestas configuran las FASES 4 y 5 (y el perfil documental de FASE 7).

1. ¿Qué unidades existen y cómo se llaman formalmente (RRHH, DAF, SECPLA, Jurídica, Control, Secretaría)?
2. ¿Quién inicia el requerimiento de contratación y en qué formato (memorándum, formulario)?
3. ¿Quién autoriza el requerimiento: Alcalde o Administrador Municipal con facultad delegada? ¿Existe decreto de delegación?
4. ¿Quién emite el CDP y con qué datos (folio, cuenta, subtítulo/ítem)? ¿Se exige antes de redactar el contrato?
5. ¿Cómo controlan el tope del 10% del gasto en personal de planta? ¿Quién lo certifica?
6. ¿Qué documentos exigen al prestador antes de firmar? ¿Cuáles son bloqueantes y cuáles pueden adjuntarse después?
7. ¿Qué unidades visan el borrador de contrato y el decreto, y en qué orden? ¿Visan en papel o digital?
8. ¿Qué pasa cuando una unidad observa o repara? ¿Quién subsana y cómo se re-visa?
9. ¿Control Interno tiene carril de reparos formales? ¿En qué estado queda el expediente mientras tanto?
10. ¿Quién firma primero: prestador, Alcalde, Secretario? ¿El prestador firma el contrato separado o integrado al decreto?
11. ¿Quién numera y fecha el decreto? ¿Formato del correlativo (Decreto Exento N° X / Alcaldicio N° X)?
12. ¿Usan plataforma externa de firma electrónica avanzada? ¿Cuál? ¿Qué documentos pasan por ella?
13. ¿Quién registra en SIAPER y en qué plazo real lo hacen? ¿Cómo guardan el comprobante?
14. ¿A quién distribuyen copias del decreto tramitado y cómo registran la recepción?
15. ¿Cómo manejan subrogancias (vacaciones, ausencias) de Alcalde/Secretario/jefes? ¿Decreto de subrogancia?
16. ¿Plazos típicos de cada etapa y cuellos de botella conocidos?
17. Contrataciones express / trabajos simples: ¿cómo las hacen hoy y qué documentos omiten?
18. Estructura del decreto local: ¿VISTOS/CONSIDERANDOS/RESOLUTIVA? ¿Textos fijos institucionales (acta concejo, fallo tribunal electoral, presupuesto anual)?

---

## 9. Riesgos y notas técnicas

- **Legal (firma):** OTP + rúbrica es firma electrónica simple con evidencia (Ley 19.799), no FEA. Validar con Jurídica/Control antes de vender "cumple lo legal". FEA externa como complemento ingerido.
- **Legal (jornada):** `hours_weekly` fija es indicio de subordinación/dependencia (riesgo de recalificación laboral por Contraloría). Parametrizar y advertir; conservar en perfil Cunco como práctica local.
- **SIAPER:** sin API pública de CGR → tracking + export manual. El plazo de 15 días hábiles es obligación legal ya citada en los VISTOS del sistema.
- **Documentación:** fuente de verdad = este plan + `plan_de_desarrollo.md` actualizado. README/Requerimientos/Contexto deben reescribirse (FASE 9).
- **Multi-tenant diferido:** FASES 1–5 sobre single-tenant no se pierden; los catálogos nuevos (tipos de documento, permisos, textos fijos, política de firma, etapas de visación) deben nacer como **datos configurables**.
- **SQLite:** WAL, un archivo por tenant, backups por volumen Railway; concurrencia limitada por tenant (asumible para el tamaño de una muni).
- **OCR:** no remover el parche Windows de PaddleOCR (`FLAGS_enable_pir_in_executor=0`, `FLAGS_enable_pir_api=0`) en `ocr_service.py`.
- **Seguridad:** CSRF global (FASE 1), rate limiting OTP (FASE 3), `SECRET_KEY` sin fallback dev en producción (FASE 3), validación de uploads (FASE 9).

---

## 10. Definición de "producto completo" (definition of done)

- [ ] Flujo legal de 6 etapas cubierto extremo a extremo en el perfil ESTANDAR_CGR.
- [ ] Matriz de permisos por sección aplicada en servidor y UI; Secretario numera/firma; SUPERADMIN no firma.
- [ ] Carpeta de antecedentes con checklist, vencimientos y gate express (kit mínimo antes de emitir decreto).
- [ ] Firmas OTP unificadas + orden legal + FEA complementaria + validación pública por código.
- [ ] Requerimiento + CDP pasivo como prerequisitos; máquina de estados completa y auditada.
- [ ] Visaciones configurables con carril de Control, subrogaciones y alertas de estancamiento.
- [ ] SIAPER con plazo de 15 días hábiles, alertas, paquete de exportación y distribución registrada.
- [ ] Multi-tenant con BD por muni y onboarding de nueva municipalidad en un comando.
- [ ] Motor de plantillas (ESTANDAR_CGR + CUNCO) con CONSIDERANDOS y cláusulas como datos.
- [ ] Tests automatizados verdes + documentación alineada + validación jurídica del piloto.
