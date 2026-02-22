from django.contrib import admin
from .models import Department, Course, Enrollment, CalendarEvent, Task, TaskSubmission

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'code', 'teacher', 'price', 'is_published')
    list_filter = ('is_published', 'teacher', 'price')
    search_fields = ('title', 'code', 'description')
    ordering = ('title',)

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'grade', 'enrolled_at')
    list_filter = ('course', 'enrolled_at')
    search_fields = ('student__username', 'course__title')

@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'start_time', 'is_exam')
    list_filter = ('is_exam', 'course')
    search_fields = ('title',)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'due_date', 'weight')
    list_filter = ('course',)

@admin.register(TaskSubmission)
class TaskSubmissionAdmin(admin.ModelAdmin):
    list_display = ('task', 'student', 'is_completed', 'progress_percentage')
    list_filter = ('is_completed', 'task__course')
    search_fields = ('student__username', 'task__title')
