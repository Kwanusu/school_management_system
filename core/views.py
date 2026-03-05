from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from .models import Task, Course, TaskSubmission, CalendarEvent, Enrollment
from .serializers import (
    CourseDetailSerializer, TaskSerializer, EnrollmentSerializer, 
    CourseSerializer, CourseCreateSerializer, CalendarEventSerializer, 
    TaskSubmissionSerializer
)

User = get_user_model()

class CourseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing course instances.
    Provides logic for public listings, teacher-owned courses, and student enrollments.
    """
    serializer_class = CourseSerializer

    def get_queryset(self):
        """
        Filters courses based on user role:
        - Anonymous: Publicly published free courses.
        - Teacher: Courses where they are the primary instructor.
        - Student: Enrolled courses or public free courses.
        - Admin: All courses.
        """
        user = self.request.user
        base_queryset = Course.objects.annotate(student_count=Count('enrolled_students'))

        if user.is_anonymous:
            return base_queryset.filter(is_published=True, price=0)
        if user.role == 'TEACHER':
            return base_queryset.filter(teacher=user)
        if user.role == 'STUDENT':
            return base_queryset.filter(Q(enrolled_students=user) | Q(is_published=True, price=0)).distinct()
        return base_queryset.all()

    def get_permissions(self):
        """
        Allows anyone to view course lists/details, but requires authentication for modifications.
        """
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        """
        Returns specialized serializers for different actions:
        - create: CourseCreateSerializer (handles teacher assignment).
        - retrieve: CourseDetailSerializer (includes full related data).
        - default: CourseSerializer.
        """
        if self.action == 'create':
            return CourseCreateSerializer
        if self.action == 'retrieve':
            return CourseDetailSerializer
        return CourseSerializer

    def perform_create(self, serializer):
        """
        Assigns the current user as the teacher of the course.
        Only users with the 'TEACHER' role or Admin status can create courses.
        """
        if self.request.user.role != 'TEACHER' and not self.request.user.is_staff:
            raise PermissionDenied("Only teachers can create courses.")
        serializer.save(teacher=self.request.user)

    @action(detail=False, methods=['get'], url_path='my-courses')
    def my_courses(self, request):
        """
        GET /api/courses/my-courses/
        Dashboard endpoint for teachers to view courses they have created.
        """
        if request.user.role != 'TEACHER':
            return Response({"detail": "Access restricted to teachers."}, status=403)
        
        courses = Course.objects.filter(teacher=request.user).annotate(
            student_count=Count('enrolled_students')
        )
        serializer = self.get_serializer(courses, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='enrolled-courses')
    def enrolled_courses(self, request):
        """
        GET /api/courses/enrolled-courses/
        Dashboard endpoint for students to view courses they are currently enrolled in.
        """
        if request.user.role != 'STUDENT':
            return Response({"detail": "Access restricted to students."}, status=403)

        courses = Course.objects.filter(enrolled_students=request.user).annotate(
            student_count=Count('enrolled_students')
        ).distinct()
        serializer = self.get_serializer(courses, many=True)
        return Response(serializer.data)


class TaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Course Tasks.
    Visibility is restricted to courses the user is involved in.
    """
    serializer_class = TaskSerializer

    def get_queryset(self):
        """
        Restricts task visibility:
        - Students: Tasks from courses they are enrolled in.
        - Teachers: Tasks from courses they teach.
        """
        user = self.request.user
        if user.role == 'STUDENT':
            return Task.objects.filter(course__enrolled_students=user)
        if user.role == 'TEACHER':
            return Task.objects.filter(course__teacher=user)
        return Task.objects.all()


class EnrollmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet to manage student enrollments.
    Allows staff to create records and students to view their own enrollment history.
    """
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Students see only their own enrollment records; Staff see all.
        """
        user = self.request.user
        if user.role == 'STUDENT':
            return Enrollment.objects.filter(student=user)
        return Enrollment.objects.all()

    def perform_create(self, serializer):
        """
        Restricts enrollment creation to Admins or Teachers.
        """
        if self.request.user.role not in ['ADMIN', 'TEACHER']:
            raise PermissionDenied("Only staff can enroll students.")
        serializer.save()


class CalendarEventViewSet(viewsets.ModelViewSet):
    """
    ViewSet for course-related calendar events.
    """
    serializer_class = CalendarEventSerializer

    def get_queryset(self):
        """
        Filters events based on the user's participation in the associated course.
        """
        user = self.request.user
        if user.role == 'STUDENT':
            return CalendarEvent.objects.filter(course__enrolled_students=user)
        if user.role == 'TEACHER':
            return CalendarEvent.objects.filter(course__teacher=user)
        return CalendarEvent.objects.all()


class TaskSubmissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling student task submissions and teacher grading.
    """
    serializer_class = TaskSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Ensures students see only their work, and teachers see work for their courses.
        """
        user = self.request.user
        if user.role == 'STUDENT':
            return TaskSubmission.objects.filter(student=user)
        return TaskSubmission.objects.filter(task__course__teacher=user)

    def perform_create(self, serializer):
        """
        Automatically assigns the submitting user as the 'student' on the submission.
        """
        serializer.save(student=self.request.user)

    @action(detail=True, methods=['post'], url_path='grade')
    def grade(self, request, pk=None):
        """
        POST /api/submissions/{id}/grade/
        Allows a teacher to apply a grade and feedback to a specific submission.
        Validates that the requester is the instructor for the course.
        """
        submission = self.get_object()
        if request.user != submission.task.course.teacher:
            raise PermissionDenied("You are not authorized to grade this course.")

        grade = request.data.get('grade')
        feedback = request.data.get('feedback', '')

        if grade is None:
            return Response({"error": "Grade is required"}, status=400)

        submission.grade = grade
        submission.feedback = feedback
        submission.is_graded = True 
        submission.save()

        serializer = self.get_serializer(submission)
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def enroll_student(request, course_id):
    """
    Functional view to manually enroll a student into a course via email.
    
    Expects:
    - course_id: URL parameter
    - email: JSON body key
    
    Actions:
    1. Validates user exists and has 'STUDENT' role.
    2. Adds user to Course.enrolled_students (M2M).
    3. Creates/Updates Enrollment tracking model record.
    """
    email = request.data.get('email')
    try:
        student = User.objects.get(email__iexact=email)
        course = Course.objects.get(id=course_id)
        
        if student.role != 'STUDENT':
            return Response({"message": "User is not a student."}, status=400)
            
        if course.enrolled_students.filter(id=student.id).exists():
            return Response({"message": "Student already enrolled"}, status=400)
            
        course.enrolled_students.add(student)
        Enrollment.objects.get_or_create(student=student, course=course)
        
        return Response({"message": f"Successfully enrolled {email}"}, status=200)

    except User.DoesNotExist:
        return Response({"message": "No student found with this email"}, status=404)
    except Course.DoesNotExist:
        return Response({"message": "Course not found"}, status=404)