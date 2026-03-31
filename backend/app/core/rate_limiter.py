from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared rate-limiter instance.
# Import this in main.py (to register on app) and in endpoints (to apply limits).
limiter = Limiter(key_func=get_remote_address)
