from django.contrib import admin

from .models import Task, TaskComment


class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 0
    raw_id_fields = ("author",)
    readonly_fields = ("created_at", "updated_at", "mentions")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "status",
        "priority",
        "visibility",
        "organization",
        "creator",
        "assignee",
        "due_date",
    )
    list_filter = ("status", "priority", "visibility")
    search_fields = ("title", "description", "tags")
    raw_id_fields = ("organization", "creator", "assignee", "team")
    readonly_fields = ("created_at", "updated_at", "completed_at")
    date_hierarchy = "due_date"
    inlines = [TaskCommentInline]


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ("task", "author", "created_at")
    search_fields = ("body",)
    raw_id_fields = ("task", "author")
    readonly_fields = ("mentions", "created_at", "updated_at")
