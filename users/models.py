from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

# Create your models here.

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        TEACHER = "TEACHER", "Teacher"
        STUDENT = "STUDENT", "Student"
        
    role = models.CharField(max_length=25,choices=Role.choices, default=Role.ADMIN)
    bio = models.TextField(blank=True)
    email = models.EmailField(unique=True)
    
    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER 

class AuditLog(models.Model):
    action_type = models.CharField(max_length=50)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    # Relational link: One User has many Logs
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        related_name='logs', 
        on_delete=models.SET_NULL, 
        null=True
    )

    class Meta:
        ordering = ['-timestamp'] # Latest logs first    
    
       
