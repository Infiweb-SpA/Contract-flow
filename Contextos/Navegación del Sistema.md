# FLUJO DE VISTAS, WIREFRAMES Y COMPONENTES DE INTERFAZ (SIGH-MUNI)

## 1. Mapa de Navegación del Sistema

```
[ VISTA 00: Login ]
       │
       ├──► [ VISTA 01: Dashboard Principal ]
       │
       ├──► [ VISTA 02A: Creador / Armador de Contratos ] (NUEVO)
       │        ├── Formulario Guiado de Redacción de Contrato
       │        ├── Asignación Dinámica de Funciones
       │        └── Generación y Exportación a PDF Borrador
       │
       ├──► [ VISTA 02B: Ingestión / Carga de Contratos ]
       │        ├── Subida de PDFs
       │        └── Ejecución del Motor PaddleOCR / Extracción
       │
       ├──► [ VISTA 03: Split-View (Vista Dividida Creador/Editor vs PDF) ]
       │        ├── Panel Izquierdo: Ficha y Funciones Editables
       │        └── Panel Derecho: Visor del Contrato PDF
       │
       └──► [ VISTA 04: Bandeja de Aprobación de Pagos Mensuales ]
                ├── Checklist de Funciones vs Informe Actividades
                └── Aprobaciones por Rol (Jefe Depto / RRHH / Finanzas)
```

---

## 2. Detalle de Pantallas Clave

### VISTA 02A: Creador / Armador de Contratos (`/contracts/create`)
- **Propósito:** Armar nuevos contratos dentro de la plataforma.
- **Componentes:**
  - Selector de Prestador (búsqueda por RUT o botón "Nuevo Prestador").
  - Formulario de datos del contrato: Cargo, Departamento, N° Decreto, Monto Bruto Mensual, Fechas de Inicio y Término.
  - Editor dinámico de Funciones: Lista donde se pueden agregar cláusulas y cometidos con un botón `+ Agregar Función`.
  - Botón: `Generar PDF Contrato` (Descarga el PDF formateado para derivar a la plataforma externa de firma).

---

### VISTA 03: Visor de Desglose y Edición Split View (`/contracts/<id>/edit`)

```
+-------------------------------------------------------------------------------------------------------+
| BUSCADOR RÁPIDO: [ RUT / Nombre Prestador              ] [🔍 BUSCAR]   | MODO: [ CREADO / CARGADO OCR ] |
+-------------------------------------------------------------+-----------------------------------------+
| PANEL IZQUIERDO: FICHA Y FUNCIONES EDITABLES                | PANEL DERECHO: DOCUMENTO PDF            |
|                                                             |                                         |
| [ Nombre: Juan ] [ Apellidos: Pérez García ] [ RUT: ... ]   | +-------------------------------------+ |
| [ Cargo: Aseo y Limpieza ] [ Depto: DIDECO             ]   | | REPUBLICA DE CHILE                  | |
| [ Decreto N°: 1042 ] [ Monto Bruto: $550.000          ]     | | MUNICIPALIDAD DE ...                | |
|                                                             | |                                     | |
| CLÁUSULA DE FUNCIONES (ARMADA O EXTRAÍDA POR OCR):          | | DECRETO ALCALDICIO N° 1042          | |
| +---------------------------------------------------------+ | | ...                                 | |
| | [1] Barre dependencias municipales                     | | | Se contrata a Don JUAN PÉREZ      | |
| | [2] Limpia vidrios y ventanales externos               | | | GARCÍA, RUT 12.345.678-9 para:    | |
| | [3] Revisa cámaras de inspección y desagües            | | | 1. Barre dependencias...          | |
| | [+ AGREGAR OTRA FUNCIÓN]                                | | | 2. Limpia vidrios...              | |
| +---------------------------------------------------------+ | +-------------------------------------+ |
|                                                             |                                         |
| [ 💾 GUARDAR CAMBIOS Y CONFIRMAR ] [ ❌ CANCELAR ]          | [ 🖨️ IMPRIMIR ] [ ⬇️ DESCARGAR PDF ]  |
+-------------------------------------------------------------+-----------------------------------------+
```