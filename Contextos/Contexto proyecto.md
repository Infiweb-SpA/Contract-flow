# CONTEXTO DEL PROYECTO: SISTEMA INTEGRADO DE GESTIÓN, CREACIÓN Y REVISIÓN DE HONORARIOS MUNICIPALES (SIGH-MUNI)

## 1. Visión General
El **Sistema Integrado de Gestión, Creación y Revisión de Honorarios Municipales (SIGH-MUNI)** es una solución SaaS integral diseñada para resolver el ciclo de vida completo de los contratos a honorarios en municipalidades de Chile.

El sistema permite **armar y confeccionar nuevos contratos a honorarios** a partir de plantillas estandarizadas, así como **revisar y desglosar contratos existentes** subidos al sistema. Dado que el proceso de firma digital se encuentra 100% externalizado en una plataforma dedicada de la municipalidad, SIGH-MUNI asume la validez de los documentos firmados ingresados y se concentra exclusivamente en:
1. La **generación/armado** de nuevos borradores y contratos.
2. El **desglose automático de funciones y datos** mediante OCR (PaddleOCR / pdfplumber) para revisión de RRHH y departamentos.
3. El **flujo de aprobación de pagos mensuales** basado en el cumplimiento de tareas desglosadas.

---

## 2. Antecedentes y Necesidad Operativa
1. **Doble Necesidad (Creación y Revisión):** Las municipalidades no solo necesitan revisar los contratos que llegan de plataformas externas, sino también contar con un generador de contratos que arme las cláusulas, decretos y montos sin errores de digitación.
2. **Firmas Externalizadas:** La validación y ejecución de la firma digital ya ocurre fuera de este sistema. Por tanto, no se requiere validar firmas digitales PAdES/CAdES ni certificados PKI; los documentos subidos para revisión se procesan asumiendo su condición de firmados/válidos.
3. **Flujo de Trabajo Simplificado:** Una vez creados o cargados los contratos, la herramienta permite a los Jefes de Departamento y RRHH modificar, ajustar y aprobar la lista de funciones que desempeñará cada prestador para autorizar sus estados de pago mensuales.

---

## 3. Entorno Tecnológico y Configuración de Desarrollo
- **Modelo de Despliegue:** SaaS contenerizado montado en **Railway**.
- **Backend:** Python 3.11 + Flask (Arquitectura modular con Blueprints).
- **Entorno de Desarrollo:** Instalación global de librerías de Python en el equipo de desarrollo (sin entornos virtuales `venv`), optimizando la reutilización de dependencias para proyectos futuros.
- **Base de Datos Exclusiva:** **SQLite** (con modo WAL habilitado y almacenamiento persistente en Railway). No se requiere ni se migrará a ningún motor de base de datos externo (como PostgreSQL/MySQL), garantizando despliegues ultra rápidos y livianos.
- **Frontend:** Tailwind CSS + Vanilla JS / Alpine.js (UI ligera, rápida y adaptable).
- **Motor de OCR / Extracción:** PaddleOCR (`PP-OCRv4` / `es`) + `pdfplumber` + `pdf2image` con `poppler-utils`.

---

## 4. Alcance del Proyecto y Cronograma (Entrega: Octubre)
- **Semanas 1-2:** Arquitectura en Flask + SQLite, roles de usuario y módulo de armador/creador de contratos.
- **Semanas 3-4:** Módulo de ingestión de PDFs y motor PaddleOCR para extracción automática de funciones.
- **Semanas 5-6:** Interfaz Split-View (Vista Creador/Editor vs PDF) y flujo jerárquico de aprobación de pagos.
- **Semanas 7-8:** Módulo de reportes/métricas, pruebas finales y paso a producción en Railway.