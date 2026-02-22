from rest_framework import serializers
from django.db.models import Avg
from .models import Course, Enrollment, CalendarEvent, Task, TaskSubmission, Department
from analytics.models import SystemLog

# --- Supporting Serializers ---

class DepartmentSerializer(serializers.ModelSerializer):
    """Metadata for grouping courses."""
    class Meta:
        model = Department
        fields = ['id', 'name']

class CalendarEventSerializer(serializers.ModelSerializer):
    """Standalone and nested calendar data."""
    course_title = serializers.ReadOnlyField(source='course.title')

    class Meta:
        model = CalendarEvent
        fields = ['id', 'course', 'course_title', 'title', 'start_time', 'end_time', 'is_exam']

class TaskSerializer(serializers.ModelSerializer):
    """Course-related assignments."""
    class Meta:
        model = Task
        fields = ['id', 'course', 'title', 'due_date', 'weight']

class SystemLogSerializer(serializers.ModelSerializer):
    """Read-only audit trail for Admin oversight."""
    user_name = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = SystemLog
        fields = ['id', 'action', 'user', 'user_name', 'timestamp', 'details']
        read_only_fields = fields

# --- Core Logic Serializers ---

class TaskSubmissionSerializer(serializers.ModelSerializer):
    """Handles students uploading work and teachers grading it."""
    task_title = serializers.ReadOnlyField(source='task.title')
    student_name = serializers.ReadOnlyField(source='student.username')

    class Meta:
        model = TaskSubmission
        fields = [
            'id', 'task', 'task_title', 'student', 'student_name', 
            'file', 'is_completed', 'progress_percentage'
        ]
        read_only_fields = ['student']

class CourseSerializer(serializers.ModelSerializer):
    """The central hub for course data including nested tasks and events."""
    teacher_name = serializers.ReadOnlyField(source='teacher.username')
    events = CalendarEventSerializer(many=True, read_only=True)
    tasks = TaskSerializer(many=True, read_only=True)
    student_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'code', 'description', 'price', 
            'is_published', 'thumbnail', 'teacher', 'teacher_name',
            'events', 'tasks', 'student_count'
        ]

    def validate(self, data):
        """Ensures consistent business logic for public vs paid courses."""
        price = data.get('price', getattr(self.instance, 'price', 0))
        is_published = data.get('is_published', getattr(self.instance, 'is_published', False))

        if is_published and price > 0:
            raise serializers.ValidationError(
                {"is_published": "Paid courses cannot be set to Public (Free access)."}
            )
        return data

class EnrollmentSerializer(serializers.ModelSerializer):
    """Manages student registration and calculates real-time progress."""
    student_name = serializers.ReadOnlyField(source='student.username')
    course_title = serializers.ReadOnlyField(source='course.title')
    overall_progress = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = [
            'id', 'student', 'student_name', 'course', 
            'course_title', 'grade', 'overall_progress', 'enrolled_at'
        ]

    def get_overall_progress(self, obj):
        """Calculates the average progress across all submissions for this enrollment."""
        avg = TaskSubmission.objects.filter(
            student=obj.student, 
            task__course=obj.course
        ).aggregate(Avg('progress_percentage'))['progress_percentage__avg']
        
        return round(avg, 2) if avg is not None else 0