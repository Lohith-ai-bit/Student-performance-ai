from fastapi import APIRouter

from app.api.routes import admin, advanced, auth, dashboards, faculty, ml, records, students

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(students.router)
api_router.include_router(faculty.router)
api_router.include_router(records.router)
api_router.include_router(admin.router)
api_router.include_router(ml.router)
api_router.include_router(dashboards.router)
api_router.include_router(advanced.router)
