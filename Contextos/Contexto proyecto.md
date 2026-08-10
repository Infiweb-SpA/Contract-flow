# CONTEXTO DEL PROYECTO: SISTEMA INTEGRADO DE GESTIÓN, CREACIÓN Y REVISIÓN DE HONORARIOS MUNICIPALES (SIGH-MUNI)

## 1. Visión General
El **Sistema Integrado de Gestión, Creación Y Revisión de Honorarios Municipales (SIGH-MUNI)** es una solución SaaS integral diseñada para resolver el ciclo de vida completo de los contratos a honorarios y sus estados de pago en municipalidades de Chile.

El sistema permite **armar y confeccionar nuevos contratos a honorarios** a partir de plantillas estandarizadas, así como **revisar y desglosar contratos existentes** subidos al sistema. Dado que el proceso de firma digital se encuentra 100% externalizado en la plataforma previa y dedicada de la municipalidad, SIGH-MUNI no interviene ni valida firmas digitales, asumiendo la validez legal de los documentos firmados ingresados y concentrándose exclusivamente en:
1. La **generación/armado** de nuevos borradores y plantillas de contratos.
2. La **ingesta, OCR y desglose automático de funciones y datos** (PaddleOCR / pdfplumber) para la revisión estructurada.
3. El **Buscador Global Omnipresente (`Ctrl + K`)** para la localización e identificación inmediata de contratos, expedientes y pagos "en el aire".
4. El **flujo de revisión y aprobación de pagos mensuales** estructurado en las 4 etapas internas de RRHH y la verificación del cumplimiento de tareas desglosadas.

---

## 2. Antecedentes y Necesidad Operativa
1. **Doble Necesidad (Creación y Ingesta para Revisión):** Las municipalidades requieren confeccionar contratos con cláusulas y montos estandarizados sin errores de digitación, así como cargar contratos firmados externamente para iniciar el circuito de pagos.
2. **Firmas 100% Externalizadas:** La ejecución de la firma digital por parte de las autoridades se realiza de forma totalmente independiente fuera de este sistema. SIGH-MUNI procesa los documentos PDF asumiendo su condición de firmados y válidos.
3. **Buscador y Trazabilidad de Expedientes:** Debido al volumen masivo de contratos y al riesgo de extravío de expedientes físicos/digitales entre departamentos (ej. contratos de DIDECO o prestadores específicos), el sistema cuenta con un buscador universal con alertas de tiempo de estancamiento.
4. **Flujo Interno de Pagos en RRHH:** Una vez ingresados los contratos firmados, la plataforma guía el expediente a través del circuito de 4 etapas internas de Recursos Humanos para auditar el cumplimiento de funciones y autorizar la liberación del pago mensual.

---

## 3. Entorno Tecnológico y Configuración de Desarrollo
- **Modelo de Despliegue:** SaaS contenerizado montado en **Railway**.
- **Backend:** Python 3.11 + Flask (Arquitectura modular con Blueprints).
- **Entorno de Desarrollo:** Instalación global de librerías de Python en el equipo de desarrollo (sin entornos virtuales `venv`), optimizando la reutilización de dependencias para proyectos futuros.
- **Base de Datos Exclusiva:** **SQLite** (con modo WAL habilitado y almacenamiento persistente en Railway). No se requiere ni se migrará a ningún motor de base de datos externo (como PostgreSQL/MySQL), garantizando despliegues ultra rápidos y livianos.
- **Frontend & UI:** Tailwind CSS + Vanilla JS / Alpine.js (UI ligera, rápida y adaptable) con módulo Split-View para revisión OCR y Buscador Global en Topbar (`Ctrl + K`).
- **Motor de OCR / Extracción:** PaddleOCR (`PP-OCRv4` / `es`) + `pdfplumber` + `pdf2image` con `poppler-utils`.

---

## 4. Alcance del Proyecto y Cronograma (Entrega: Octubre)
- **Semanas 1-2:** Arquitectura en Flask + SQLite, roles de usuario, Buscador Global (`Ctrl + K`) y armador/creador de contratos.
- **Semanas 3-4:** Módulo de ingestión de PDFs firmados externamente y motor PaddleOCR para extracción automática de funciones.
- **Semanas 5-6:** Interfaz Split-View (Visor PDF vs Formulario/Checklist) y flujo jerárquico de aprobación de pagos en 4 etapas de RRHH.
- **Semanas 7-8:** Módulo de reportes/métricas, pruebas finales y paso a producción en Railway.

# Propuesta de Diseño UX/UI y Arquitectura de Interfaz
## Sistema Integrado de Gestión, Creación y Revisión de Honorarios Municipales (SIGH-MUNI)

---

## 1. Enfoque Ministerial/Municipal y Alcance Operativo

El sistema **SIGH-MUNI** se concibe como una solución de gestión y trazabilidad de expedientes en entornos municipales. Respetando las directrices de la administración municipal:

1. **Sin Módulo de Firma Digital Integrado:** La validación y ejecución de la firma digital se encuentra **100% externalizada** en la plataforma previa de la municipalidad. SIGH-MUNI asume la validez legal de los documentos en PDF ingresados y se concentra exclusivamente en la gestión, despiece de funciones y aprobación de estados de pago.
2. **Protección de Datos Sensibles:** El sistema utiliza campos y flujos estandarizados de la administración pública chilena (estándar Contraloría / Ley de Honorarios) para la demostración del proyecto, permitiendo parametrizar campos específicos una vez aprobado.
3. **Trazabilidad y Localización Inmediata:** Resuelve la problemática de expedientes "perdidos" o traspasos manuales entre dependencias mediante un **Buscador Global Omnipresente** que indica la ubicación exacta de cada contrato/pago en tiempo real.

---

## 2. Buscador Global Omnipresente de Contratos y Pagos (`Ctrl + K`)

Ubicado de forma permanente en la barra superior (Top Navigation Bar) de la plataforma, accesible desde cualquier módulo.

### 2.1 Criterios de Búsqueda Soportados:
- **Datos del Prestador:** RUT (con o sin puntos/guión), Nombre, Apellidos.
- **Identificadores del Expediente:** Número de Contrato (ej. `CT-2026-0809`), Número de Decreto Alcaldicio.
- **Filtro Orgánico:** Departamento/Unidad Origen (DIDECO, SECPLA, DOM, etc.).
- **Filtro por Estado del Flujo:** `Contrato Ingresado (Firmado)`, `En Revisión RRHH (Nivel 1-4)`, `Pago Aprobado`, `Pago Observado`.

### 2.2 Visualización de Resultados:
- **Ubicación Exacta:** Muestra en qué bandeja o escritorio se encuentra el expediente (ej. *RRHH - Etapa 2: Revisión de Funciones*).
- **Alerta Trazable de Tiempo:** Indicador visual de días en la etapa actual (Verde: < 2 días; Amarillo: 3-5 días; Rojo: > 5 días - Alerta de estancamiento).

---

## 3. Arquitectura del Flujo Estándar de Trabajo

### 3.1 Ingesta de Contratos Firmados Externamente
1. El contrato es subido en formato PDF tras haber completado su circuito de firma en el sistema externo municipal.
2. El motor OCR (`pdfplumber` / `PaddleOCR`) procesa el documento y extrae automáticamente los datos del prestador, vigencia, montos y desglose de funciones.

### 3.2 Circuito Estandarizado de Revisión de Pagos (4 Niveles RRHH)
Para autorizar los pagos mensuales basados en los contratos firmados, el expediente recorre las 4 etapas estándar del departamento de Recursos Humanos:

1. **Nivel 1 — Recepción e Ingesta Documental:** Carga del informe mensual de actividades y verificación de concordancia con el contrato firmado.
2. **Nivel 2 — Evaluación de Cumplimiento de Funciones:** Checklist ítem por ítem (`Cumplido`, `Parcial`, `No Cumplido`) de las tareas pactadas en el contrato.
3. **Nivel 3 — Visado Administrativo de RRHH:** Revisión de antecedentes, cálculo de honorario líquido/bruto e impositivos.
4. **Nivel 4 — Aprobación y Liberación de Pago:** Emisión del visto bueno final para el envío a Finanzas/Tesorería.

---

## 4. Diseño de Pantallas Clave

### 4.1 Dashboard Principal (Bandeja Multinivel)
- **Header Global:** Logotipo institucional, Buscador Omnipresente (`Ctrl + K`), Rol activo y Notificaciones.
- **Métricas Operativas (KPIs):** Contratos Activos, Pagos Pendientes en Mi Nivel, Expedientes Detenidos (+5 días), Pagos Aprobados del Mes.
- **Bandeja de Trabajo:** Tabla de alta densidad con filtros rápidos por Departamento y Estado.

### 4.2 Módulo Split-View (Revisión de Informe vs Checklist)
- **Panel Izquierdo (40% de ancho):** Visor interactivo del documento PDF (Contrato Firmado / Informe Mensual) con herramientas de zoom y búsqueda.
- **Panel Derecho (60% de ancho):** Formulario estructurado con los datos extraídos, checklist de funciones, caja de observaciones por función y botones de acción rápida de alto contraste (`[Aprobar]`, `[Observar]`, `[Rechazar]`).