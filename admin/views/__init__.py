"""
Admin Views Router
==================

Routes admin panel pages based on menu selection.

Available Pages:
- Update warehouse: Edit/delete existing warehouses
- Add warehouse: Create new warehouse configurations
- Add customer: Manage customer database

Usage:
    from admin.views import admin_router
    admin_router("Update warehouse")

Related Files:
- admin/app.py: Standalone admin panel
- admin/views/*.py: Individual page implementations
"""

from .update_warehouse import page_update_warehouse
from .add_warehouse import page_add_warehouse
from .add_customer import page_add_customer


# Page registry (supports multiple naming formats)
_PAGES = {
    "update warehouse": page_update_warehouse,
    "add warehouse": page_add_warehouse,
    "add customer": page_add_customer,
    "Update warehouse": page_update_warehouse,
    "Add warehouse": page_add_warehouse,
    "Add customer": page_add_customer,
    "Update Warehouse": page_update_warehouse,
    "Add Warehouse": page_add_warehouse,
    "Add Customer": page_add_customer,
}


def admin_router(choice: str):
    """
    Route to appropriate admin page based on selection.
    
    Args:
        choice: Page name from sidebar menu
        
    Returns:
        Rendered page (or default to update_warehouse)
    """
    page_func = _PAGES.get(choice, page_update_warehouse)
    return page_func()