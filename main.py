import os
import xmlrpc.client
from fastapi import FastAPI, HTTPException

app = FastAPI()

# 1. إعداد المتغيرات وتنظيف الرابط
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
    return {"status": "API running successfully"}


@app.get("/get_wallet/{phone}")
def get_wallet(phone: str):
    try:
        # 1. تسجيل الدخول
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
        
        if not uid:
            raise HTTPException(status_code=401, detail="فشل تسجيل الدخول في أودو!")

        models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
        
        # 2. البحث عن العميل بواسطة رقم الهاتف
        partner_ids = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'res.partner', 'search',
            [[['phone', '=', phone]]]
        )

        if not partner_ids:
            return {"status": "error", "message": "العميل غير موجود في أودو"}

        partner_id = partner_ids[0]

        # جلب بيانات العميل الأساسية
        partner_data = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'res.partner', 'read',
            [[partner_id]],
            {'fields': ['id', 'name', 'phone', 'credit', 'currency_id']}
        )[0]

        wallet_balance = 0.0
        found_wallet = False

        # 3. محاولة جلب رصيد المحفظة من موديول eWallet / Loyalty Card
        try:
            card_ids = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'loyalty.card', 'search',
                [[['partner_id', '=', partner_id]]]
            )
            
            if card_ids:
                cards_data = models.execute_kw(
                    ODOO_DB, uid, ODOO_PASSWORD,
                    'loyalty.card', 'read',
                    [card_ids],
                    {'fields': ['points', 'program_type']}
                )
                
                # جمع نقاط/رصيد المحفظة للعميل
                total_points = sum(c.get('points', 0.0) for c in cards_data)
                wallet_balance = total_points
                found_wallet = True
        except Exception:
            # في حال لم يكن موديول loyalty.card مثبتاً
            pass

        # إذا لم نجد محفظة eWallet نستخدم قيمة credit الاحتياطية
        final_balance = wallet_balance if found_wallet else partner_data.get("credit", 0.0)
        currency_name = partner_data['currency_id'][1] if partner_data.get('currency_id') else "ILS"

        return {
            "status": "success",
            "customer_id": partner_data.get("id"),
            "name": partner_data.get("name"),
            "phone": partner_data.get("phone"),
            "wallet_balance": final_balance,
            "currency": currency_name
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Odoo Error: {str(e)}")
