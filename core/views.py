from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from .serializers import TaskSerializer, EnrollmentSerializer
from .models import Task

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'STUDENT':
            # Students only see tasks for courses they are enrolled in
            return Task.objects.filter(course__enrollment__student=user)
        if user.role == 'TEACHER':
            # Teachers see tasks for courses they teach
            return Task.objects.filter(course__teacher=user)
        return Task.objects.all() # Admin

class EnrollmentViewSet(viewsets.ModelViewSet):
    """
    Logic: Teachers and Admins can create enrollments.
    Students can only view their own.
    """
    serializer_class = EnrollmentSerializer

    def perform_create(self, serializer):
        if self.request.user.role not in ['ADMIN', 'TEACHER']:
            raise PermissionDenied("Only staff can enroll students.")
        serializer.save()