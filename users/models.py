from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        TEACHER = "TEACHER", "Teacher"
        STUDENT = "STUDENT", "Student"
        
    role = models.CharField(max_length=25,choices=Role.choices, default=Role.ADMIN)
    bio = models.TextField(blank=True)
    
    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER    
