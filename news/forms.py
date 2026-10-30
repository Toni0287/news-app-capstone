"""Forms used by the News application's HTML views.

Covers registration, login, and creating or editing articles,
newsletters and publishers.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Article, Newsletter, Publisher


class RegisterForm(UserCreationForm):
    """Registration form that captures role and optional publisher affiliation."""

    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=CustomUser.ROLE_CHOICES)
    publisher = forms.ModelChoiceField(
        queryset=Publisher.objects.all(),
        required=False,
        empty_label='Independent (no publisher)',
        help_text='Journalists and editors may be affiliated with a publisher.',
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'role', 'publisher', 'password1', 'password2']


class LoginForm(forms.Form):
    """Simple username/password login form."""

    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)


class ArticleForm(forms.ModelForm):
    """Form for creating and editing articles."""

    class Meta:
        model = Article
        fields = ['title', 'content', 'publisher']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 10}),
        }


class NewsletterForm(forms.ModelForm):
    """Form for creating and editing newsletters; restricts articles to approved ones."""

    class Meta:
        model = Newsletter
        fields = ['title', 'description', 'articles']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'articles': forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        """Create the form and limit the article choices to approved
        articles only.

        :param args: Positional arguments passed to ``ModelForm``
        :param kwargs: Keyword arguments passed to ``ModelForm``
        """
        super().__init__(*args, **kwargs)
        self.fields['articles'].queryset = Article.objects.filter(approved=True)


class PublisherForm(forms.ModelForm):
    """Form for editors to create a new publisher."""

    class Meta:
        model = Publisher
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
