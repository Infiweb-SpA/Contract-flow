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