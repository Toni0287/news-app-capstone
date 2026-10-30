from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Publisher, Article, Newsletter


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'publisher', 'is_staff']
    list_filter = ['role', 'publisher']
    fieldsets = UserAdmin.fieldsets + (
        ('Role & Affiliation', {'fields': ('role', 'publisher')}),
        ('Subscriptions', {'fields': ('subscribed_publishers', 'subscribed_journalists')}),
    )


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'publisher', 'approved', 'created_at']
    list_filter = ['approved', 'publisher']
    search_fields = ['title', 'content']
    actions = ['approve_articles']

    def approve_articles(self, request, queryset):
        queryset.update(approved=True)
    approve_articles.short_description = 'Approve selected articles'


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'created_at']
    search_fields = ['title']
    filter_horizontal = ['articles']
