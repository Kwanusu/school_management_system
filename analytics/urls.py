from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SystemLogViewSet

# 1. Initialize the router
router = DefaultRouter()

# 2. Register the ViewSet
# This will create endpoints like:
# GET /api/logs/ -> List all logs
# GET /api/logs/{id}/ -> Retrieve a specific log
router.register(r'logs', SystemLogViewSet, basename='systemlog')

# 3. Define the URL patterns
urlpatterns = [
    path('', include(router.urls)),
]



