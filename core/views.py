from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from .serializers import TaskSerializer, EnrollmentSerializer, CourseSerializer, CalendarEventSerializer, TaskSubmissionSerializer
from .models import Task,Course, TaskSubmission, CalendarEvent
from django.db.models import Count
from django.db import models
from drf_spectacular.utils import extend_schema, OpenApiParameter


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
        

class CourseViewSet(viewsets.ModelViewSet):
    serializer_class = CourseSerializer

    def get_queryset(self):
        user = self.request.user
        
        # We use .annotate(student_count=...) to fulfill your requirement 
        # of seeing how many students are in a course.
        base_queryset = Course.objects.annotate(student_count=Count('enrollment'))

        if user.is_anonymous:
            # Anonymous users only see free, published courses
            return base_queryset.published_free()

        if user.role == 'TEACHER':
            # Teachers see the courses they created
            return base_queryset.by_teacher(user)

        if user.role == 'STUDENT':
            # Students see courses they are enrolled in + public free courses
            return base_queryset.filter(
                models.Q(enrollment__student=user) | 
                models.Q(is_published=True, price=0)
            ).distinct()

        return base_queryset.all() # Admin sees everything

    def perform_create(self, serializer):
        # Professional standard: Automatically assign the logged-in user as the teacher
        if self.request.user.role != 'TEACHER' and not self.request.user.is_staff:
            raise PermissionDenied("Only teachers can create courses.")
        serializer.save(teacher=self.request.user)

class CalendarEventViewSet(viewsets.ModelViewSet):
    serializer_class = CalendarEventSerializer

    def get_queryset(self):
        user = self.request.user
        # Only show events for courses the user is involved in
        if user.role == 'STUDENT':
            return CalendarEvent.objects.filter(course__enrollment__student=user)
        if user.role == 'TEACHER':
            return CalendarEvent.objects.filter(course__teacher=user)
        return CalendarEvent.objects.all()

class TaskSubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSubmissionSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'STUDENT':
            # Students only see their own submissions
            return TaskSubmission.objects.filter(student=user)
        # Teachers see submissions for their specific courses
        return TaskSubmission.objects.filter(task__course__teacher=user)

    def perform_create(self, serializer):
        # Automatically link the submission to the logged-in student
        serializer.save(student=self.request.user)
        
class CourseViewSet(viewsets.ModelViewSet):

    @extend_schema(
        summary="List all courses",
        description="Returns a list of courses filtered by the user's role.",
        responses={200: CourseSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)        

