# admin/views/__init__.py

from .update_warehouse import page_update_warehouse
from .add_warehouse import page_add_warehouse
from .add_customer import page_add_customer

_PAGES = {
    "Update warehouse": page_update_warehouse,
    "Add warehouse": page_add_warehouse,
    "Add customer": page_add_customer,
}

def admin_router(choice: str):
    _PAGES.get(choice, page_update_warehouse)()
