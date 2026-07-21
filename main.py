import os
import xmlrpc.client
from fastapi import FastAPI, HTTPException

app = FastAPI()

# قراءة المتغيرات من Render
ODOO_URL = os.getenv("ODOO_URL", "").rstrip('/')
ODOO_DB = os.getenv("ODOO_DB", "")
ODOO_USERNAME = os.getenv("ODOO_USERNAME", "")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "")

@app.get("/")
def home():
    return {"status": "API running"}

@app.get("/get_wallet/{phone}")
def get_wallet(phone: str):
    try:
        # 1. الاتصال بسيرفر الأمان وتسجيل الدخول
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        
        # محاولة الحصول على UID
        uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
        
        if not uid:
            raise HTTPException(
                status_code=401, 
                detail="فشل تسجيل الدخول في أودو! اسم المستخدم أو كلمة المرور/API Key أو اسم القاعدة غير صحيح"
            )

        # 2. الاتصال بسيرفر البيانات بعد نجاح الدخول
        models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
        
        # البحث عن العميل بواسطة رقم الهاتف
        partner_ids = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'res.partner', 'search',
            [[['phone', '=', phone]]]
        )

        if not partner_ids:
            # تجربة البحث في حقل الموبايل إذا لم يجده في الهاتف
            partner_ids = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'res.partner', 'search',
                [[['mobile', '=', phone]]]
            )

        if not partner_ids:
            return {"status": "error", "message": "العميل غير موجود"}

        # جلب بيانات العميل (الاسم والرصيد)
        partner_data = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'res.partner', 'read',
            [partner_ids],
            {'fields': ['name', 'credit', 'phone', 'mobile']}
        )

        return {
            "status": "success",
            "data": partner_data[0]
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Odoo Error: {str(e)}")
