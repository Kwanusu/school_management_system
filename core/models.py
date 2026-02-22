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
        """
        Professional Logic: Validation happens before the data hits the database.
        Constraint: Course can be public ONLY if it is free.
        """
        if self.is_published and self.price > 0:
            raise ValidationError(
                {"is_published": "Paid courses cannot be set to Public (Free access)."}
            )

    def save(self, *args, **kwargs):
        self.full_clean() # Force validation on every save
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} (${self.price})" 
    
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