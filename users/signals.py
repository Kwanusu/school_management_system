from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import AuditLog
from core.models import TaskSubmission

User = get_user_model()

@receiver(post_save, sender=User)
def log_user_registration(sender, instance, created, **kwargs):
    if created:
        # This is the automated logging your project focuses on
        AuditLog.objects.create(
            action_type="USER_REGISTRATION",
            message=f"New {instance.role} account created: {instance.username}",
            user=instance  # Relational link to the new user
        )
        
@receiver(post_save, sender=TaskSubmission)
def log_grade_entry(sender, instance, created, **kwargs):
    # Only log if it's an update (not creation) and a grade was just added
    if not created and instance.grade is not None:
        AuditLog.objects.create(
            action_type="GRADE_ASSIGNED",
            message=f"Instructor {instance.task.course.teacher.username} graded {instance.student.username}'s work in {instance.task.course.name}.",
            user=instance.task.course.teacher
        )        