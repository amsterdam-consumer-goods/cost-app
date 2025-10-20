# admin/views/__init__.py
from .update_warehouse import page_update_warehouse
from .add_warehouse import page_add_warehouse
from .add_customer import page_add_customer

_PAGES = {
    # küçük harfli (admin/app.py ile aynı)
    "Update warehouse": page_update_warehouse,
    "Add warehouse": page_add_warehouse,
    "Add customer": page_add_customer,
    # olası büyük harfli varyantlar
    "Update Warehouse": page_update_warehouse,
    "Add Warehouse": page_add_warehouse,
    "Add Customer": page_add_customer,
}

def admin_router(choice: str):
    # Eşleşmezse güvenli varsayılan: Update
    return _PAGES.get(choice, page_update_warehouse)()
