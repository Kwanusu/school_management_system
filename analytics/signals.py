from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import Enrollment
from .models import SystemLog

@receiver(post_save, sender=Enrollment)
def log_grade_change(sender, instance, created, **kwargs):
    if not created:
        SystemLog.objects.create(
           action="GRADE_UPDATE",
            details={
                "student": instance.student.username,
                "course": instance.course.title,
                "new_grade": str(instance.grade)
            }
        )