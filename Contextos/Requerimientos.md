# REQUERIMIENTOS FUNCIONALES Y NO FUNCIONALES DEL SISTEMA (SIGH-MUNI)

## 1. REQUERIMIENTOS FUNCIONALES (RF)

### RF-01: Autenticación, Control de Accesos por Roles (RBAC) y Bitácora
- **RF-01.1:** Autenticación de usuarios mediante RUT/Email y Contraseña.
- **RF-01.2:** Roles de usuario:
  1. *SuperAdmin:* Administración general del sistema.
  2. *Admin RRHH:* Creación de borradores de contratos, carga de contratos externos y gestión de usuarios.
  3. *Jefe de Departamento / Contraparte Técnica:* Creación de requerimientos de contratación, revisión de funciones y primera aprobación del pago mensual.
  4. *Finanzas / Control:* Aprobación final del pago y liberación de liquidaciones.
- **RF-01.3 (Bitácora de Auditoría):** Registro inmutable en la tabla `audit_logs` de cada acción: creación de contrato, modificación de funciones, visado de pagos y observaciones.

### RF-02: Módulo Armador / Creador de Contratos a Honorarios
- **RF-02.1 (Generador de Contratos):** Formulario guiado para redactar y estructurar nuevos contratos a honorarios a partir de plantillas tipo aprobadas por la municipalidad.
- **RF-02.2 (Campos Dinámicos del Contrato):**
  - Datos del Prestador (RUT, Nombres, Apellidos, Domicilio, Profesión/Oficio).
  - Datos Administrativos (Departamento solicitante, N° Decreto, Fecha, Programa Municipal).
  - Condiciones Económicas (Monto mensual bruto, vigencia inicio/fin).
  - Cláusula de Funciones (Listado dinámico de tareas asignadas al prestador).
- **RF-02.3 (Exportación a PDF):** Generación automática del borrador/contrato final en PDF listo para ser derivado a la plataforma de firma digital externa.

### RF-03: Módulo de Ingestión y Extracción OCR (Para Contratos Cargados)
- **RF-03.1 (Carga de Documentos Externalizados):** Carga individual o masiva de PDFs de contratos provenientes de la plataforma externa de firma. *No se realiza ninguna validación técnica de firma digital (se asume de pleno firmada y válida).*
- **RF-03.2 (Motor de Extracción OCR):**
  - Extracción de texto directo con `pdfplumber` en PDFs nativos.
  - Extracción mediante `PaddleOCR` para PDFs escaneados.
- **RF-03.3 (Parser de Datos):** Extracción automática de RUT, Nombre, Cargo, Monto y Desglose de Funciones a partir del documento subido.

### RF-04: Módulo de Desglose, Edición y Asignación de Funciones (Split-View)
- **RF-04.1 (Interfaz Dividida):** Vista de pantalla dividida con los datos/funciones desglosados a la izquierda y el visor PDF a la derecha.
- **RF-04.2 (Gestión de Funciones):** Permitir agregar, reordenar, modificar o eliminar funciones extraídas o redactadas.

### RF-05: Módulo de Flujo de Aprobación de Pagos Mensuales
- **RF-05.1 (Checklist de Cumplimiento):** Control mensual donde la contraparte técnica valida el cumplimiento de cada función del contrato antes de liberar el pago.
- **RF-05.2 (Circuito de Aprobación):** *Pendiente* $
ightarrow$ *Visado Jefe Depto* $
ightarrow$ *Aprobado RRHH* $
ightarrow$ *Aprobado Finanzas*.

---

## 2. REQUERIMIENTOS NO FUNCIONALES (RFN)

- **RFN-01 (Simplicidad de Arquitectura Base de Datos):** El sistema utilizará exclusivamente **SQLite** como motor de base de datos persistente (fichero `.db` en volumen Railway), garantizando velocidad, cero dependencias de servicios externos y despliegues instantáneos.
- **RFN-02 (Rendimiento OCR):** Extracción y desglose de contratos en un tiempo máximo de 4.5 segundos.
- **RFN-03 (Despliegue y Hosting):** Servidor Flask en **Railway** con volumen montado para almacenamiento de la base de datos SQLite y PDFs.