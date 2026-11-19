# -*- coding: utf-8 -*-
"""
Migración idempotente Fase 6: suscripción granular a eventos de notificación.
Agrega columna disabled_notifications (JSON) a users.
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
    if 'disabled_notifications' not in cols:
        cur.execute('ALTER TABLE users ADD COLUMN disabled_notifications TEXT')
        print('  + Columna users.disabled_notifications agregada')
    else:
        print('  = Columna users.disabled_notifications ya existe')
    conn.commit()
    conn.close()
    print('Migración Fase 6 (eventos de notificación) completada.')


if __name__ == '__main__':
    migrate()