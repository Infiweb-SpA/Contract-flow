# -*- coding: utf-8 -*-
"""
Migración idempotente Fase 5: notificaciones por correo.
Agrega columna receive_email_notifications a users.
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
    if 'users' not in existing:
        print('ERROR: tabla users no existe')
        conn.close()
        return
    cols = {row[1] for row in cur.execute("PRAGMA table_info(users)")}
    if 'receive_email_notifications' not in cols:
        cur.execute('ALTER TABLE users ADD COLUMN receive_email_notifications INTEGER NOT NULL DEFAULT 0')
        print('  + Columna users.receive_email_notifications agregada')
    else:
        print('  = Columna users.receive_email_notifications ya existe')
    conn.commit()
    conn.close()
    print('Migración Fase 5 (notificaciones) completada.')


if __name__ == '__main__':
    migrate()