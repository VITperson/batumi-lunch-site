from . import admin, auth, menu, orders

routers = [
    auth.router,
    menu.router,
    orders.router,
    admin.router,
]

__all__ = ["routers"]
