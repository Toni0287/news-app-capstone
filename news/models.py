"""Database models for the News application.

Defines publishers, users with reader/journalist/editor roles,
articles and newsletters.
"""
from django.db import models
from django.contrib.auth.models import AbstractUser


class Publisher(models.Model):
    """A publication that employs editors and journalists.

    :param name: Unique name of the publisher
    :type name: str
    :param description: Optional description of the publisher
    :type description: str, optional
    """

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    """Extended user with role-based fields for readers, journalists, and editors.

    :param role: One of ``reader``, ``journalist`` or ``editor``,
        defaults to ``reader``
    :type role: str
    :param publisher: Publisher a journalist or editor works for,
        defaults to None (independent)
    :type publisher: :class:`Publisher`, optional
    """

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
        """Save the user, then clear reader-only subscriptions for
        journalists and editors.

        :param args: Positional arguments passed to ``Model.save``
        :param kwargs: Keyword arguments passed to ``Model.save``
        """
        super().save(*args, **kwargs)
        if self.role in ('journalist', 'editor'):
            self.subscribed_publishers.clear()
            self.subscribed_journalists.clear()

    def __str__(self):
        return f'{self.username} ({self.role})'


class Article(models.Model):
    """A news article written by a journalist.

    Articles are hidden from readers until an editor approves them.

    :param title: Headline of the article
    :type title: str
    :param content: Body text of the article
    :type content: str
    :param author: Journalist who wrote the article
    :type author: :class:`CustomUser`
    :param approved: Whether an editor has approved the article,
        defaults to False
    :type approved: bool
    :param publisher: Publisher the article belongs to, or None if the
        journalist published it independently
    :type publisher: :class:`Publisher`, optional
    """

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
    """A curated collection of articles created by a journalist.

    :param title: Title of the newsletter
    :type title: str
    :param description: Optional summary of the newsletter
    :type description: str, optional
    :param author: Journalist who created the newsletter
    :type author: :class:`CustomUser`
    :param articles: Articles included in the newsletter
    :type articles: list of :class:`Article`
    """

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
