"""
API Routes

Route handlers organized by resource.
"""

from . import health
from . import events
from . import participants
from . import admin
from . import auth

__all__ = ["health", "events", "participants", "admin", "auth"]