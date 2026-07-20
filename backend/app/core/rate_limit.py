"""
Shared slowapi Limiter instance.

Kept in its own module (not main.py) so route files can import `limiter`
and decorate individual endpoints without a circular import on `app`.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
