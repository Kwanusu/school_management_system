from rest_framework.exceptions import PermissionDenied
from .serializers import CourseDetailSerializer, TaskSerializer, EnrollmentSerializer, CourseSerializer, CourseCreateSerializer, CalendarEventSerializer, TaskSubmissionSerializer
from .models import Task,Course, TaskSubmission, CalendarEvent
from django.db.models import Count
from django.db import models
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q, Count
from rest_framework.exceptions import PermissionDenied
from users.models import User



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
    # Default fallback serializer
    serializer_class = CourseSerializer

    def get_queryset(self):
        user = self.request.user
        # Base logic with student annotations
        base_queryset = Course.objects.annotate(student_count=Count('enrollment'))

        if user.is_anonymous:
            return base_queryset.filter(is_published=True, price=0)

        if user.role == 'TEACHER':
            # Teachers see their own courses (including drafts)
            return base_queryset.filter(teacher=user)

        if user.role == 'STUDENT':
            # Students see what they bought OR what is free/published
            return base_queryset.filter(
                Q(enrollment__student=user) | Q(is_published=True, price=0)
            ).distinct()

        return base_queryset.all()
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        """
        Critical Fix: Ensure we use the CreateSerializer 
        when POSTing to handle the teacher_id and topics.
        """
        if self.action == 'create':
            return CourseCreateSerializer
        if self.action == 'retrieve':
            return CourseDetailSerializer
        return CourseSerializer

    def perform_create(self, serializer):
        """
        Sets the teacher before saving to prevent IntegrityError.
        This teacher object is passed into serializer.create() 
        via validated_data['teacher'].
        """
        if self.request.user.role != 'TEACHER' and not self.request.user.is_staff:
            raise PermissionDenied("Only teachers can create courses.")
            
        # Passing 'teacher' here is what fills that NULL column in your DB!
        serializer.save(teacher=self.request.user)

    @action(detail=False, methods=['get'], url_path='my-courses')
    def my_courses(self, request):
        if request.user.role != 'TEACHER':
            return Response({"detail": "Not a teacher account."}, status=status.HTTP_403_FORBIDDEN)
            
        courses = Course.objects.filter(teacher=request.user).annotate(
            student_count=Count('enrollment')
        )
        # Using the base serializer for list view
        serializer = self.get_serializer(courses, many=True)
        return Response(serializer.data)


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
            return TaskSubmission.objects.filter(student=user)
        return TaskSubmission.objects.filter(task__course__teacher=user)
    
    def get_queryset(self):
        user = self.request.user
        
        # Layer 1: If you are a student, you ONLY see your own rows.
        # You cannot access /api/submissions/10/ if it belongs to someone else.
        if user.role == 'STUDENT':
            return TaskSubmission.objects.filter(student=user)
            
        # Layer 2: Teachers only see submissions for their own courses.
        return TaskSubmission.objects.filter(task__course__teacher=user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

    @action(detail=True, methods=['patch', 'post'], permission_classes=[permissions.IsAuthenticated])
    def grade(self, request, pk=None):
        """
        Endpoint: POST /api/core/submissions/{id}/grade/
        Allows a teacher to grade a specific submission.
        """
        submission = self.get_object()
        
        # Security: Ensure only the instructor of the course can grade this
        if request.user != submission.task.course.teacher:
            raise PermissionDenied("You are not authorized to grade this course.")

        # Validation: Check if grade and feedback are in the request
        grade = request.data.get('grade')
        feedback = request.data.get('feedback', '')

        if grade is None:
            return Response({"error": "Grade is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Update the submission fields
        submission.grade = grade
        submission.feedback = feedback
        submission.is_graded = True # Assuming you have this field
        submission.save()

        # Return the updated submission data
        serializer = self.get_serializer(submission)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enroll_student(request, course_id):
    email = request.data.get('email')
    try:
        student = User.objects.get(email=email)
        course = Course.objects.get(id=course_id)
        
        # Prevent double enrollment
        if course.enrolled_students.filter(id=student.id).exists():
            return Response({"message": "Student already enrolled"}, status=400)
            
        course.enrolled_students.add(student)
        return Response({"message": "Enrollment successful"}, status=200)
    except User.DoesNotExist:
        return Response({"message": "No student found with this email"}, status=404)    
        
