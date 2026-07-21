from fastapi import FastAPI, HTTPException
import xmlrpc.client

app = FastAPI()

ODOO_URL = "https://delicate0.odoo.com"
ODOO_DB = "delicate0"
ODOO_USER = "issamhalawa97@gmail.com"
ODOO_PASS = "123456789" # كلمة مرور أو API Key الخاصة بك

def get_odoo_connection():
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, {})
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    return uid, models

@app.get("/")
def home():
    return {"status": "API running"}

@app.get("/get_wallet/{phone}")
def get_wallet(phone: str):
    uid, models = get_odoo_connection()
    partner_ids = models.execute_kw(ODOO_DB, uid, ODOO_PASS, 'res.partner', 'search', [[['phone', '=', phone]]])
    if not partner_ids:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    cards = models.execute_kw(ODOO_DB, uid, ODOO_PASS, 'loyalty.card', 'search_read', 
                              [[['partner_id', '=', partner_ids[0]]]], 
                              {'fields': ['code', 'points']})
    if not cards:
        raise HTTPException(status_code=404, detail="eWallet not found")
    
    return {"phone": phone, "card_code": cards[0]['code'], "balance": cards[0]['points']}
