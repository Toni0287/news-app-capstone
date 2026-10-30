"""Django REST Framework serializers for the News application API.

Convert publishers, users, articles and newsletters to and from JSON.
"""
from rest_framework import serializers
from .models import Article, Newsletter, Publisher, CustomUser


class PublisherSerializer(serializers.ModelSerializer):
    """Serialize a :class:`~news.models.Publisher` for API responses."""

    class Meta:
        model = Publisher
        fields = ['id', 'name', 'description', 'created_at']


class UserSerializer(serializers.ModelSerializer):
    """Serialize the public details of a
    :class:`~news.models.CustomUser` (no password or subscriptions).
    """

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'role', 'publisher']


class ArticleSerializer(serializers.ModelSerializer):
    """Serialize an :class:`~news.models.Article` for reading.

    The author and publisher are nested objects, and the approval
    status and timestamps are read-only.
    """

    author = UserSerializer(read_only=True)
    publisher = PublisherSerializer(read_only=True)

    class Meta:
        model = Article
        fields = ['id', 'title', 'content', 'author', 'created_at',
                  'updated_at', 'approved', 'publisher']
        read_only_fields = ['approved', 'created_at', 'updated_at']


class ArticleCreateSerializer(serializers.ModelSerializer):
    """Used when a journalist creates an article via the API."""

    class Meta:
        model = Article
        fields = ['id', 'title', 'content', 'publisher']


class NewsletterSerializer(serializers.ModelSerializer):
    """Serialize a :class:`~news.models.Newsletter` with its author and
    the full details of each included article.
    """

    author = UserSerializer(read_only=True)
    articles = ArticleSerializer(many=True, read_only=True)

    class Meta:
        model = Newsletter
        fields = ['id', 'title', 'description', 'created_at', 'author', 'articles']
