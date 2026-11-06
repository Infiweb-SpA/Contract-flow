# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from app import create_app
from app.models.contract import Contract
from app import db as _db

app = create_app()
app.config['TESTING'] = True
client = app.test_client()
with client.session_transaction() as sess:
    sess['user_id'] = 1
    sess['user_role'] = 'SUPERADMIN'

TINY_SIG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
TINY_SIG2 = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=='

r = client.post('/contracts/create', data={
    'provider_id': '2', 'department_id': '1',
    'contract_number': 'CT-DBG-SIG', 'contract_date': '2026-11-06',
    'position_title': 'Debug', 'program_name': 'X',
    'payment_modality': 'MENSUAL_FIJO',
    'monthly_amount_gross': '500000', 'total_contract_amount': '2000000',
    'start_date': '2026-11-06', 'end_date': '2026-12-06',
    'functions[]': 'F', 'mayor_signature': TINY_SIG, 'secretary_signature': TINY_SIG2,
}, follow_redirects=True)
print('status', r.status_code)

with app.app_context():
    c = Contract.query.filter_by(contract_number='CT-DBG-SIG').first()
    print('mayor == est:', c.mayor_signature == TINY_SIG, '| len:', len(c.mayor_signature or ''), 'vs', len(TINY_SIG))
    print('secr  == est:', c.secretary_signature == TINY_SIG2, '| len:', len(c.secretary_signature or ''), 'vs', len(TINY_SIG2))
    if c.secretary_signature != TINY_SIG2:
        print('guardado repr:', repr(c.secretary_signature))
    import base64
    try:
        base64.b64decode(TINY_SIG2.split(',')[1] + '===')
        print('b64 secretary decodifica OK')
    except Exception as e:
        print('b64 secretary INVALIDO:', e)
    db.session.delete(c)
    db.session.commit()
