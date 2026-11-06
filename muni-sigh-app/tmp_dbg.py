# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from app import create_app

app = create_app()
app.config['TESTING'] = True
client = app.test_client()
with client.session_transaction() as sess:
    sess['user_id'] = 1
    sess['user_role'] = 'SUPERADMIN'
r = client.get('/contracts/create')
html = r.get_data(as_text=True)
import re
for m in re.finditer(r'PASO \d', html):
    print(m.start(), repr(html[m.start():m.start()+60]))
print('---')
print('PASO 2: DECRET...' in html, html.count('Paso'), html.count('PASO'))
