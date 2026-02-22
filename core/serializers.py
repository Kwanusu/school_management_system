from rest_framework import serializers
from .models import Course, Enrollment, CalendarEvent, Task, TaskSubmission

class CalendarEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarEvent
        fields = '__all__'

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'course', 'title', 'due_date', 'weight']

class TaskSubmissionSerializer(serializers.ModelSerializer):
    # We include the task title for the student's progress view
    task_title = serializers.ReadOnlyField(source='task.title')

    class Meta:
        model = TaskSubmission
        fields = ['id', 'task', 'task_title', 'student', 'file', 'is_completed', 'progress_percentage']
        read_only_fields = ['student']
        
        
class CourseSerializer(serializers.ModelSerializer):
    teacher_name = serializers.ReadOnlyField(source='teacher.username')
    # Nesting related data (Read-only for the overview)
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
        """
        Mirroring the model's clean() logic for the API layer.
        """
        # We check both the incoming data and existing instance for updates
        price = data.get('price', self.instance.price if self.instance else 0)
        is_published = data.get('is_published', self.instance.is_published if self.instance else False)

        if is_published and price > 0:
            raise serializers.ValidationError(
                "Paid courses cannot be set to Public (Free access)."
            )
        return data  
    
    
class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.ReadOnlyField(source='student.username')
    course_title = serializers.ReadOnlyField(source='course.title')
    
    # Method field to calculate progress on the fly
    overall_progress = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = ['id', 'student', 'student_name', 'course', 'course_title', 'grade', 'overall_progress', 'enrolled_at']

    def get_overall_progress(self, obj):
        # Calculates average progress of all tasks submitted by this student for this course
        submissions = TaskSubmission.objects.filter(
            student=obj.student, 
            task__course=obj.course
        )
        if not submissions.exists():
            return 0
        
        total_progress = sum(sub.progress_percentage for sub in submissions)
        return total_progress / submissions.count()          