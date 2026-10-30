from rest_framework import serializers
from .models import Article, Newsletter, Publisher, CustomUser


class PublisherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publisher
        fields = ['id', 'name', 'description', 'created_at']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'role', 'publisher']


class ArticleSerializer(serializers.ModelSerializer):
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
    author = UserSerializer(read_only=True)
    articles = ArticleSerializer(many=True, read_only=True)

    class Meta:
        model = Newsletter
        fields = ['id', 'title', 'description', 'created_at', 'author', 'articles']
