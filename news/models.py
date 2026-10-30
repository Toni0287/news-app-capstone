from django.db import models
from django.contrib.auth.models import AbstractUser


class Publisher(models.Model):
    """A publication that employs editors and journalists."""

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    """Extended user with role-based fields for readers, journalists, and editors."""

    ROLE_CHOICES = [
        ('reader', 'Reader'),
        ('journalist', 'Journalist'),
        ('editor', 'Editor'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='reader')

    # Affiliation for journalists and editors
    publisher = models.ForeignKey(
        Publisher,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='staff',
    )

    # Reader-only subscription fields (journalists/editors leave these empty)
    subscribed_publishers = models.ManyToManyField(
        Publisher,
        blank=True,
        related_name='subscribers',
    )
    subscribed_journalists = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        related_name='journalist_subscribers',
    )

    def save(self, *args, **kwargs):
        """Clear reader-specific fields for journalists and editors."""
        super().save(*args, **kwargs)
        if self.role in ('journalist', 'editor'):
            self.subscribed_publishers.clear()
            self.subscribed_journalists.clear()

    def __str__(self):
        return f'{self.username} ({self.role})'


class Article(models.Model):
    """A news article written by a journalist."""

    title = models.CharField(max_length=300)
    content = models.TextField()
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='articles',
        limit_choices_to={'role': 'journalist'},
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved = models.BooleanField(default=False)
    # Null means article was published independently by the journalist
    publisher = models.ForeignKey(
        Publisher,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='articles',
    )

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
        permissions = [
            ('approve_article', 'Can approve articles'),
        ]


class Newsletter(models.Model):
    """A curated collection of articles created by a journalist."""

    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='newsletters',
        limit_choices_to={'role': 'journalist'},
    )
    articles = models.ManyToManyField(Article, blank=True, related_name='newsletters')

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
