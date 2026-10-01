from fastapi import APIRouter

from app.api.v1 import auth, bookings, feedback, notifications, payments, providers, public
from app.api.v1.admin import catalog as admin_catalog
from app.api.v1.admin import operations as admin_operations
from app.api.v1.admin import platform as admin_platform
from app.api.v1.admin import users as admin_users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(public.router)
api_router.include_router(auth.router)
api_router.include_router(bookings.router)
api_router.include_router(providers.router)
api_router.include_router(providers.assignments)
api_router.include_router(payments.router)
api_router.include_router(feedback.reviews)
api_router.include_router(feedback.complaints)
api_router.include_router(notifications.router)

admin_router = APIRouter(prefix="/admin")
for module in (admin_platform, admin_users, admin_catalog, admin_operations):
    admin_router.include_router(module.router)
api_router.include_router(admin_router)
