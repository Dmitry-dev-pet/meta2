"""
API endpoints module.
"""

from . import import_ as import_module

import_router = import_module.router

__all__ = ["import_router"]
