from django.contrib import admin

from .models import Comment, Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "book",
        "status",
        "is_renewal",
    ]
    list_filter = ["status", "is_renewal", "is_anonymous"]
    search_fields = ["book", "author"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "subscription",
    ]
