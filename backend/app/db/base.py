"""Import all models for Alembic autogeneration."""

from __future__ import annotations

from .models.base import Base  # noqa: F401
from .models.broadcast import Broadcast  # noqa: F401
from .models.menu import MenuItem, MenuWeek  # noqa: F401
from .models.order import Order  # noqa: F401
from .models.order_window import OrderWindow  # noqa: F401
from .models.user import User  # noqa: F401
