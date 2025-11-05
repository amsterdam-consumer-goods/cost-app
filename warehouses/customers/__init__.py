"""Customer management modules."""

from .customer_loader import load_customers, get_customer_names, get_customer_addresses
from .address_utils import is_france_address, is_spain_address, extract_postal_code

__all__ = [
    "load_customers",
    "get_customer_names", 
    "get_customer_addresses",
    "is_france_address",
    "is_spain_address",
    "extract_postal_code",
]