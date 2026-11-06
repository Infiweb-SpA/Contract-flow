# -*- coding: utf-8 -*-
"""Test: reorden de pasos, firma dibujada (persistencia + PDF + preview)."""
import sys, io
import base64
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from app import create_app, db
from app.models.contract import Contract
from app import db as _db

app = create_app()
app.config['TESTING'] = True
FAIL = []

def check(cond, name):
    if cond: print('[OK]', name)
    else:
        FAIL.append(name); print('[FAIL]', name)

client = app.test_client()
with client.session_transaction() as sess:
    sess['user_id'] = 1
    sess['user_role'] = 'SUPERADMIN'

# ── 1. Orden: decretos (Paso 2) antes de Antecedentes Legales (Paso 3) ──
r = client.get('/contracts/create')
html = r.get_data(as_text=True)
i_dec = html.find('PASO 2: DECRETOS Y ANTECEDENTES PREVIOS')
i_ant = html.find('PASO 3: ANTECEDENTES LEGALES')
i_cla = html.find('PASO 4: CLÁUSULAS')
check(i_dec != -1 and i_ant != -1 and i_cla != -1, 'create: comentarios PASO 2/3/4 presentes')
check(i_dec < i_ant < i_cla, 'create: orden decretos -> legales -> clausulas')
for frag in ['signature_modal', 'signature_canvas', 'Añadir firma — Alcalde',
             'name="mayor_signature"', 'name="secretary_signature"']:
    check(frag in html, f'create contiene: {frag}')
check('/contracts/create' and r.status_code == 200, 'create GET 200')

r = client.get('/contracts/1/edit')
ehtml = r.get_data(as_text=True)
i_dec = ehtml.find('PASO 2: DECRETOS Y ANTECEDENTES PREVIOS')
i_ant = ehtml.find('PASO 3: ANTECEDENTES LEGALES')
i_cla = ehtml.find('PASO 4: CLÁUSULAS')
check(i_dec != -1 and i_ant != -1 and i_cla != -1, 'edit: comentarios PASO 2/3/4 presentes')
check(i_dec < i_ant < i_cla, 'edit: orden decretos -> legales -> clausulas')
for frag in ['signature_modal', 'signature_canvas', 'Añadir firma — Secretario']:
    check(frag in ehtml, f'edit contiene: {frag}')

# ── 2. POST create con firmas ──
# PNG reales generados con PIL (firmas distintas,como las que produce el canvas)
from PIL import Image as _PILImage
def _sig_png(color):
    px = _PILImage.new('RGBA', (200, 80), (255, 255, 255, 0))
    for x in range(180):
        for y in range(10):
            px.putpixel((x, y * 4), color)
    return 'data:image/png;base64,' + base64.b64encode(px.tobytes()).decode() if False else None

def make_sig(color):
    import io as _io
    buf = _io.BytesIO()
    px = _PILImage.new('RGBA', (200, 80), (255, 255, 255, 0))
    for y in range(4, 76, 5):
        for x in range(6, 194):
            px.putpixel((x, y), color)
    px.save(buf, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()

TINY_SIG = make_sig((10, 10, 30, 255))
TINY_SIG2 = make_sig((40, 40, 60, 255))
post = client.post('/contracts/create', data={
    'provider_id': '2', 'department_id': '1',
    'contract_number': 'CT-TEST-SIG-01', 'contract_date': '2026-11-06',
    'position_title': 'Prueba Firma', 'program_name': 'Programa Test',
    'decline_number': 'DEC-TEST', 'decline_date': '2026-11-05',
    'payment_modality': 'MENSUAL_FIJO',
    'monthly_amount_gross': '500000', 'total_contract_amount': '2000000',
    'start_date': '2026-11-06', 'end_date': '2026-12-06',
    'hours_weekly': '44', 'total_amount_words': 'dos millones',
    'provider_address': 'Av Test 123', 'provider_comuna': 'Cunco',
    'functions[]': 'Función de prueba',
    'mayor_signature': TINY_SIG, 'secretary_signature': TINY_SIG2,
}, follow_redirects=True)
check(post.status_code == 200, f'POST create -> {post.status_code}')

with app.app_context():
    c = Contract.query.filter_by(contract_number='CT-TEST-SIG-01').first()
    check(c is not None, 'contrato de firma creado')
    check(c is not None and c.mayor_signature == TINY_SIG, 'mayor_signature persistida')
    check(c is not None and c.secretary_signature == TINY_SIG2, 'secretary_signature persistida')
    cid = c.id if c else None

# ── 3. ver borrador + PDF con firmas ──
if cid:
    r = client.get(f'/contracts/{cid}/preview')
    html = r.get_data(as_text=True)
    check('Firma Secretario Municipal' in html and 'Firma del Alcalde' in html, 'preview con imgs de firma')
    check(html.count(TINY_SIG) >= 1 and html.count(TINY_SIG2) >= 1, 'preview incluye dataURL de firmas x2')

    r = client.get(f'/contracts/{cid}/download-pdf')
    buf = r.get_data()
    check(r.status_code == 200 and r.content_type == 'application/pdf', 'PDF descargado 200')
    import pymupdf
    with pymupdf.open(stream=buf, filetype='pdf') as doc:
        check(len(doc) >= 2, f'PDF paginas {len(doc)}')
        # page 2 (DECRETO) debe contener 2 imagenes de firma
        imgs_p2 = doc[1].get_images()
        check(len(imgs_p2) >= 2, f'PDF hoja 2 imagenes de firma: {len(imgs_p2)}')

# ── 4. editar sin firmas las limpia? (omitido: solo limpiar el carrito) ──
# Limpieza: borrar contrato de prueba
with app.app_context():
    c = Contract.query.filter_by(contract_number='CT-TEST-SIG-01').first()
    if c:
        db.session.delete(c)
        db.session.commit()
        print('Contrato de prueba eliminado.')

print()
if FAIL:
    print('FALLOS:', FAIL)
    sys.exit(1)
print('TODO OK')
