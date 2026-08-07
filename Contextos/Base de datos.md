# ESTRUCTURA DE BASE DE DATOS SQLITE (SIGH-MUNI)

Esquema SQL diseñado exclusivamente para **SQLite**. Incluye tablas para la creación de contratos, carga de contratos externos, desglose de funciones por OCR y flujo de pagos.

```sql
PRAGMA foreign_keys = ON;

-- ============================================================================
-- 1. DEPARTAMENTOS / UNIDADES MUNICIPALES
-- ============================================================================
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,                  -- Ej: DIDECO, SECPLA, DOM
    name TEXT NOT NULL,                         -- Nombre de la Dirección
    cost_center TEXT,                           -- Centro de Costo
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 2. USUARIOS Y ROLES
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rut TEXT NOT NULL UNIQUE,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (
        role IN ('SUPERADMIN', 'ADMIN_RRHH', 'JEFE_DEPTO', 'FINANZAS_CONTROL')
    ),
    department_id INTEGER,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
);

-- ============================================================================
-- 3. PRESTADORES DE SERVICIOS A HONORARIOS
-- ============================================================================
CREATE TABLE IF NOT EXISTS service_providers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rut TEXT NOT NULL UNIQUE,
    first_name TEXT NOT NULL,
    paternal_last_name TEXT NOT NULL,
    maternal_last_name TEXT,
    email TEXT,
    phone TEXT,
    address TEXT,
    bank_name TEXT,                             -- Banco
    account_type TEXT,                          -- Tipo de Cuenta
    account_number TEXT,                        -- N° Cuenta
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 4. CONTRATOS (CREADOS EN EL SISTEMA O CARGADOS EXTERNAMENTE)
-- ============================================================================
CREATE TABLE IF NOT EXISTS contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id INTEGER NOT NULL,
    department_id INTEGER NOT NULL,
    
    -- Origen del Contrato
    creation_type TEXT NOT NULL DEFAULT 'CREADO' CHECK (
        creation_type IN ('CREADO', 'CARGADO_EXTERNO')
    ),
    
    decline_number TEXT,                        -- N° Decreto Alcaldicio
    decline_date DATE,                          -- Fecha Decreto
    contract_number TEXT NOT NULL,              -- Correlativo contrato
    position_title TEXT NOT NULL,               -- Cargo / Servicio
    program_name TEXT,                          -- Programa municipal
    monthly_amount_gross REAL NOT NULL,         -- Monto bruto $CLP
    total_contract_amount REAL,                 -- Monto total $CLP
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    
    -- Archivo PDF y OCR
    pdf_file_path TEXT,                         -- Ruta archivo PDF
    ocr_processed INTEGER DEFAULT 0,            -- 1 si fue procesado por OCR
    
    -- Estado Administrativo
    status TEXT NOT NULL DEFAULT 'BORRADOR' CHECK (
        status IN ('BORRADOR', 'CREADO_PARA_FIRMA', 'INGRESADO', 'EN_EJECUCION', 'FINALIZADO')
    ),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (provider_id) REFERENCES service_providers(id) ON DELETE CASCADE,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE RESTRICT
);

-- ============================================================================
-- 5. FUNCIONES Y COMETIDOS (CREADOS O EXTRAÍDOS POR OCR)
-- ============================================================================
CREATE TABLE IF NOT EXISTS contract_functions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL,
    function_order INTEGER NOT NULL,            -- Orden cláusula (1, 2, 3...)
    function_description TEXT NOT NULL,         -- Texto función
    is_mandatory_for_payment INTEGER DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contract_id) REFERENCES contracts(id) ON DELETE CASCADE
);

-- ============================================================================
-- 6. PROCESO DE PAGO MENSUAL DE HONORARIOS
-- ============================================================================
CREATE TABLE IF NOT EXISTS monthly_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL,
    payment_year INTEGER NOT NULL,
    payment_month INTEGER NOT NULL,
    amount_to_pay REAL NOT NULL,
    report_file_path TEXT,                      -- Informe de actividades
    
    approval_status TEXT NOT NULL DEFAULT 'PENDIENTE_REVISION' CHECK (
        approval_status IN (
            'PENDIENTE_REVISION', 
            'VISADO_JEFE_DEPTO', 
            'APROBADO_RRHH', 
            'APROBADO_FINANZAS', 
            'OBSERVADO', 
            'RECHAZADO'
        )
    ),
    rejection_observations TEXT,
    
    reviewed_by_depto_user_id INTEGER,
    approved_by_rrhh_user_id INTEGER,
    approved_by_finanzas_user_id INTEGER,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contract_id) REFERENCES contracts(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by_depto_user_id) REFERENCES users(id),
    FOREIGN KEY (approved_by_rrhh_user_id) REFERENCES users(id),
    FOREIGN KEY (approved_by_finanzas_user_id) REFERENCES users(id),
    UNIQUE(contract_id, payment_year, payment_month)
);

-- ============================================================================
-- 7. CHECKLIST DE CUMPLIMIENTO DE FUNCIONES
-- ============================================================================
CREATE TABLE IF NOT EXISTS payment_function_checklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    monthly_payment_id INTEGER NOT NULL,
    contract_function_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'CUMPLIDO' CHECK (
        status IN ('CUMPLIDO', 'PARCIAL', 'NO_CUMPLIDO')
    ),
    comments TEXT,
    FOREIGN KEY (monthly_payment_id) REFERENCES monthly_payments(id) ON DELETE CASCADE,
    FOREIGN KEY (contract_function_id) REFERENCES contract_functions(id) ON DELETE CASCADE
);

-- ============================================================================
-- 8. BITÁCORA DE AUDITORÍA
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,                       -- Ej: CONTRACT_CREATE, CONTRACT_UPLOAD, OCR_EDIT
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    payload TEXT,                               -- JSON o texto
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- ÍNDICES DE RENDIMIENTO EN SQLITE
CREATE INDEX IF NOT EXISTS idx_contracts_provider ON contracts(provider_id);
CREATE INDEX IF NOT EXISTS idx_contracts_depto ON contracts(department_id);
CREATE INDEX IF NOT EXISTS idx_providers_rut ON service_providers(rut);
CREATE INDEX IF NOT EXISTS idx_payments_period ON monthly_payments(payment_year, payment_month, approval_status);
```