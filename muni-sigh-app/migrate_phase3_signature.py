# -*- coding: utf-8 -*-
"""
Migración idempotente Fase 3: tabla contract_signatures (rúbrica ágil).
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'contract_flow.db')

def migrate():
    if not os.path.exists(DB_PATH):
        print(f'ERROR: no existe la base de datos: {DB_PATH}')
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    existing = {row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'contract_signatures' not in existing:
        cur.execute('''
            CREATE TABLE contract_signatures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_id INTEGER NOT NULL,
                user_id INTEGER,
                signer_rut VARCHAR(20) NOT NULL,
                signer_name VARCHAR(200) NOT NULL,
                signer_role VARCHAR(50),
                signed_at DATETIME NOT NULL,
                ip_address VARCHAR(64),
                ip VARCHAR(64),
                user_agent TEXT,
                device_type VARCHAR(50),
                device_info TEXT,
                document_hash VARCHAR(64) NOT NULL,
                document_hash_sha256 VARCHAR(64),
                signature_image TEXT,
                signature_data TEXT,
                validation_code VARCHAR(64) NOT NULL UNIQUE,
                is_valid INTEGER NOT NULL DEFAULT 1,
                created_at DATETIME,
                FOREIGN KEY (contract_id) REFERENCES contracts(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        ''')
        print('  + Tabla contract_signatures creada')
    else:
        print('  = Tabla contract_signatures ya existe')
    conn.commit()
    conn.close()
    print('Migración Fase 3 completada.')

if __name__ == '__main__':
    migrate()
