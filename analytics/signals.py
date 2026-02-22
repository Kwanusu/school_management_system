from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import Enrollment
from .models import SystemLog

@receiver(post_save, sender=Enrollment)
def check_grade_change(sender, instance, created, **kwargs):
    if not created:
        SystemLog.objects.create(
            action=f"Grade updated for {instance.student.username}",
            details={"course": instance.course.title, "new_grade": str(instance.grade)}
        )