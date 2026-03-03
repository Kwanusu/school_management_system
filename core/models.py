from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings

# Create your models here.

class CourseQuerySet(models.QuerySet):
    def published_free(self):
        return self.filter(is_published=True, price=0)
    
    def by_teacher(self, user):
        return self.filter(teacher=user)

class Department(models.Model):
    name = models.CharField(max_length=100)

class Course(models.Model):
    title = models.CharField(max_length=200)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)
    
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_published = models.BooleanField(default=False)
    thumbnail = models.ImageField(upload_to='course_thumbs/', null=True, blank=True)
    
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        limit_choices_to={'role': 'TEACHER'}
    )
    
    objects = CourseQuerySet.as_manager()

    def clean(self):
            # Validation logic
            if self.is_published and self.price > 0:
                raise ValidationError("Paid courses cannot be published.")

    def save(self, *args, **kwargs):
        # If we have a teacher, we can safely clean
        if self.teacher_id: 
            self.full_clean()
        super().save(*args, **kwargs)


class Topic(models.Model):
    course = models.ForeignKey(Course, related_name='topics', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.code} - {self.title}"

class Lesson(models.Model):
    # Lesson types to differentiate between content, challenges, and projects
    LESSON_TYPES = (
        ('LESSON', 'Standard Lesson'),
        ('CHALLENGE', 'Daily Challenge'),
        ('WEEKLY_PROJECT', 'Weekly Project'),
        ('CAPSTONE', 'Capstone Project'),
    )
    
    topic = models.ForeignKey(Topic, related_name='lessons', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField(help_text="The actual reading/video material")
    lesson_type = models.CharField(max_length=20, choices=LESSON_TYPES, default='LESSON')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"[{self.lesson_type}] {self.title}"


class Enrollment(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'STUDENT'}
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'course') # Prevents double enrollment
        
        
class CalendarEvent(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=200)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_exam = models.BooleanField(default=False)

class Task(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    due_date = models.DateTimeField()
    weight = models.IntegerField(default=10) # e.g., 10% of total grade

class TaskSubmission(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file = models.FileField(upload_to='submissions/')
    is_completed = models.BooleanField(default=False)
    progress_percentage = models.IntegerField(default=0)   
    
    