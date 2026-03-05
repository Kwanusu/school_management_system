from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CourseViewSet, TaskViewSet, EnrollmentViewSet, 
    CalendarEventViewSet, TaskSubmissionViewSet, enroll_student
)

# Initialize router
router = DefaultRouter()

# Register ViewSets
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'enrollments', EnrollmentViewSet, basename='enrollment')
router.register(r'calendar', CalendarEventViewSet, basename='calendar')
router.register(r'submissions', TaskSubmissionViewSet, basename='submission')

urlpatterns = [
    # Include all auto-generated router paths
    path('', include(router.urls)),
    
    # Custom functional endpoint for manual enrollment
    # Accessible via: POST /api/courses/<id>/enroll/
    path('courses/<int:course_id>/enroll/', enroll_student, name='manual-enroll'),
]