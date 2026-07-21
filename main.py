import os
import xmlrpc.client
from fastapi import FastAPI, HTTPException

app = FastAPI()

# قراءة المتغيرات وتنظيف الرابط
raw_url = os.getenv("ODOO_URL", "").strip().rstrip('/')
if raw_url and not raw_url.startswith(("http://", "https://")):
    raw_url = f"https://{raw_url}"

if raw_url.endswith("/odoo"):
    raw_url = raw_url[:-5]

ODOO_URL = raw_url
ODOO_DB = os.getenv("ODOO_DB", "").strip()
ODOO_USERNAME = os.getenv("ODOO_USERNAME", "").strip()
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "").strip()

@app.get("/")
def home():
    return {"status": "API running"}

@app.get("/get_wallet/{phone}")
def get_wallet(phone: str):
    try:
        # 1. الاتصال وتسجيل الدخول
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
        
        if not uid:
            raise HTTPException(
                status_code=401, 
                detail="فشل تسجيل الدخول في أودو!"
            )

        # 2. الاتصال بسيرفر البيانات
        models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
        
        # البحث عن العميل بواسطة حقل phone
        partner_ids = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'res.partner', 'search',
            [[['phone', '=', phone]]]
        )

        if not partner_ids:
            return {"status": "error", "message": "العميل غير موجود في أودو"}

        # جلب اسم العميل ورصيده (credit) برقم ID
        partner_data = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'res.partner', 'read',
            [partner_ids],
            {'fields': ['name', 'credit', 'phone']}
        )

        return {
            "status": "success",
            "data": partner_data[0]
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Odoo Error: {str(e)}")
