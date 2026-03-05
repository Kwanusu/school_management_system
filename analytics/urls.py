from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SystemLogViewSet

# 1. Initialize the router
router = DefaultRouter()
router.register(r'logs', SystemLogViewSet, basename='systemlog')

# 3. Define the URL patterns
urlpatterns = [
    path('', include(router.urls)),
]



