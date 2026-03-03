from rest_framework import serializers
from django.db.models import Avg
from .models import Course, Enrollment, CalendarEvent, Task, TaskSubmission, Department, Topic, Lesson
from analytics.models import SystemLog
import json

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
    course_title = serializers.ReadOnlyField(source='task.course.name')
    student_name = serializers.ReadOnlyField(source='student.username')

    class Meta:
        model = TaskSubmission
        fields = [
            'id', 'task', 'task_title', 'course_title','student', 'student_name', 
            'file', 'is_completed', 'progress_percentage', 'created_at', 'grade'
        ]
        read_only_fields = ['student']

class CourseSerializer(serializers.ModelSerializer):
    # Mark teacher as read-only so the frontend doesn't have to send it
    teacher = serializers.StringRelatedField(read_only=True)
    topics = serializers.SerializerMethodField() # To handle the stringified JSON

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'code', 'description', 
            'price', 'is_published', 'thumbnail', 'teacher', 'topics'
        ]
    def validate(self, data):
        is_published = data.get('is_published')
        price = data.get('price', 0)

        if is_published and price > 0:
            raise serializers.ValidationError(
                {"is_published": "Paid courses cannot be set to Public (Free access)."}
            )
        return data        

    def create(self, validated_data):
        # 1. Handle the stringified 'topics' from FormData
        request = self.context.get('request')
        topics_raw = request.data.get('topics')
        
        if isinstance(topics_raw, str):
            topics_data = json.loads(topics_raw)
        else:
            topics_data = topics_raw or []

        # 2. Create the course (teacher is passed from perform_create)
        course = Course.objects.create(**validated_data)

        # 3. Create nested Topics and Lessons
        for topic_item in topics_data:
            lessons_data = topic_item.pop('lessons', [])
            topic = Topic.objects.create(course=course, **topic_item)
            for lesson_item in lessons_data:
                Lesson.objects.create(topic=topic, **lesson_item)
                
        return course

class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['id', 'title', 'lesson_type', 'order']

class TopicSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True) # Nesting lessons!

    class Meta:
        model = Topic
        fields = ['id', 'title', 'lessons', 'order']

class CourseDetailSerializer(serializers.ModelSerializer):
    topics = TopicSerializer(many=True, read_only=True) # Nesting topics!

    class Meta:
        model = Course
        fields = ['id', 'title', 'code', 'description', 'topics']
        
    def update(self, instance, validated_data):
        topics_data = validated_data.pop('topics', [])
        # 1. Update basic course info
        instance.title = validated_data.get('title', instance.title)
        instance.save()

        # 2. Update or Create Topics
        for topic_data in topics_data:
            topic_id = topic_data.get('id')
            if topic_id:
                Topic.objects.filter(id=topic_id, course=instance).update(**topic_data)
            else:
                Topic.objects.create(course=instance, **topic_data)
                
        return instance    

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
    
    
class CourseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'title', 'code', 'description', 'price', 'is_published', 'thumbnail']
        read_only_fields = ['teacher']
        # We don't include 'teacher' in fields because we assign it manually

    def create(self, validated_data):
        # 1. Get user from context
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("Authentication required.")

        # 2. Extract and parse Topics (React sends them as stringified JSON in FormData)
        topics_raw = request.data.get('topics')
        topics_data = json.loads(topics_raw) if isinstance(topics_raw, str) else (topics_raw or [])

        # 3. Inject teacher into validated_data
        validated_data['teacher'] = request.user

        # 4. Create the Course
        course = Course.objects.create(**validated_data)

        # 5. Handle Nested Topics/Lessons
        for topic_item in topics_data:
            lessons_data = topic_item.pop('lessons', [])
            # Create Topic
            topic = Topic.objects.create(course=course, title=topic_item.get('title'), order=topic_item.get('order'))
            
            # Create Lessons
            for lesson_item in lessons_data:
                Lesson.objects.create(
                    topic=topic,
                    title=lesson_item.get('title'),
                    content=lesson_item.get('content', ''),
                    lesson_type=lesson_item.get('lesson_type', 'LESSON'),
                    order=lesson_item.get('order')
                )
                
        return course


        
        
        