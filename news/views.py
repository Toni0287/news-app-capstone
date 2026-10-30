from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings

from .models import Article, Newsletter, CustomUser, Publisher
from .forms import RegisterForm, LoginForm, ArticleForm, NewsletterForm, PublisherForm


# ── Authentication ──────────────────────────────────────────────────────────

def register_view(request):
    """Display the registration form and create a new user account."""
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = form.cleaned_data['role']
            user.publisher = form.cleaned_data.get('publisher')
            user.save()
            from django.contrib.auth.models import Group
            group_map = {
                'reader': 'Readers',
                'journalist': 'Journalists',
                'editor': 'Editors',
            }
            group_name = group_map.get(user.role)
            if group_name:
                group, _ = Group.objects.get_or_create(name=group_name)
                user.groups.add(group)
            login(request, user)
            messages.success(request, f'Welcome, {user.username}!')
            return redirect('article_list')
    else:
        form = RegisterForm()
    return render(request, 'news/register.html', {'form': form})


def login_view(request):
    """Display the login form and authenticate the user."""
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
            )
            if user is not None:
                login(request, user)
                return redirect('article_list')
            messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    return render(request, 'news/login.html', {'form': form})


def logout_view(request):
    """Log the current user out and redirect to the login page."""
    logout(request)
    return redirect('login')


# ── Articles ─────────────────────────────────────────────────────────────────

@login_required
def article_list(request):
    """Display all approved articles to authenticated users."""
    articles = Article.objects.filter(approved=True).select_related('author', 'publisher')
    return render(request, 'news/article_list.html', {'articles': articles})


@login_required
def article_detail(request, pk):
    """Display a single article; unapproved articles are restricted to the author and editors."""
    article = get_object_or_404(Article, pk=pk)
    if not article.approved:
        if request.user.role != 'editor' and request.user != article.author:
            messages.error(request, 'This article has not been approved yet.')
            return redirect('article_list')
    return render(request, 'news/article_detail.html', {'article': article})


@login_required
def article_create(request):
    """Allow journalists to submit a new article for editorial approval."""
    if request.user.role != 'journalist':
        messages.error(request, 'Only journalists can create articles.')
        return redirect('article_list')
    if request.method == 'POST':
        form = ArticleForm(request.POST)
        if form.is_valid():
            article = form.save(commit=False)
            article.author = request.user
            article.save()
            messages.success(request, 'Article submitted for approval.')
            return redirect('my_articles')
    else:
        form = ArticleForm()
    return render(request, 'news/article_form.html', {'form': form, 'action': 'Create'})


@login_required
def article_edit(request, pk):
    """Allow journalists (own articles) and editors (any article) to edit an article."""
    article = get_object_or_404(Article, pk=pk)
    if request.user.role not in ('journalist', 'editor'):
        messages.error(request, 'You do not have permission to edit articles.')
        return redirect('article_list')
    if request.user.role == 'journalist' and article.author != request.user:
        messages.error(request, 'You can only edit your own articles.')
        return redirect('my_articles')
    if request.method == 'POST':
        form = ArticleForm(request.POST, instance=article)
        if form.is_valid():
            form.save()
            messages.success(request, 'Article updated.')
            return redirect('article_detail', pk=article.pk)
    else:
        form = ArticleForm(instance=article)
    return render(request, 'news/article_form.html',
                  {'form': form, 'action': 'Edit', 'article': article})


@login_required
def article_delete(request, pk):
    """Allow journalists (own articles) and editors (any article) to delete an article."""
    article = get_object_or_404(Article, pk=pk)
    if request.user.role not in ('journalist', 'editor'):
        messages.error(request, 'You do not have permission to delete articles.')
        return redirect('article_list')
    if request.user.role == 'journalist' and article.author != request.user:
        messages.error(request, 'You can only delete your own articles.')
        return redirect('my_articles')
    if request.method == 'POST':
        article.delete()
        messages.success(request, 'Article deleted.')
        if request.user.role == 'journalist':
            return redirect('my_articles')
        return redirect('article_list')
    return render(request, 'news/article_confirm_delete.html', {'article': article})


@login_required
def article_approve(request, pk):
    """Editors review and approve submitted articles."""
    if request.user.role != 'editor':
        messages.error(request, 'Only editors can approve articles.')
        return redirect('article_list')
    article = get_object_or_404(Article, pk=pk)
    if request.method == 'POST':
        article.approved = True
        article.save()
        _notify_subscribers(article)
        messages.success(request, f'"{article.title}" has been approved and subscribers notified.')
        return redirect('article_pending')
    return render(request, 'news/article_approve.html', {'article': article})


@login_required
def article_pending(request):
    """Display the approval queue to editors, with options to edit, approve, or reject articles."""
    if request.user.role != 'editor':
        messages.error(request, 'Only editors can view the approval queue.')
        return redirect('article_list')
    articles = Article.objects.filter(approved=False).select_related('author', 'publisher')
    return render(request, 'news/article_pending.html', {'articles': articles})


@login_required
def my_articles(request):
    """Show a journalist all of their articles (approved and pending) with management options."""
    if request.user.role != 'journalist':
        messages.error(request, 'This page is for journalists only.')
        return redirect('article_list')
    articles = Article.objects.filter(author=request.user).select_related('publisher')
    return render(request, 'news/my_articles.html', {'articles': articles})


def _notify_subscribers(article):
    """Email all readers subscribed to the article's journalist or publisher on approval."""
    subscriber_qs = CustomUser.objects.none()
    subscriber_qs = subscriber_qs | CustomUser.objects.filter(
        subscribed_journalists=article.author
    )
    if article.publisher:
        subscriber_qs = subscriber_qs | CustomUser.objects.filter(
            subscribed_publishers=article.publisher
        )
    emails = list(subscriber_qs.values_list('email', flat=True).distinct())
    if not emails:
        return
    subject = f'New article: {article.title}'
    body = (
        f'Hello,\n\n'
        f'A new article has been published on NewsApp:\n\n'
        f'Title: {article.title}\n'
        f'Author: {article.author.username}\n\n'
        f'{article.content[:300]}...\n\n'
        f'Log in to read the full article.'
    )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, emails, fail_silently=True)
    except Exception as e:
        print(f'Email notification error: {e}')


# ── Publishers ────────────────────────────────────────────────────────────────

@login_required
def publisher_create(request):
    """Allow editors to create a new publisher."""
    if request.user.role != 'editor':
        messages.error(request, 'Only editors can create publishers.')
        return redirect('article_list')
    if request.method == 'POST':
        form = PublisherForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Publisher created.')
            return redirect('article_list')
    else:
        form = PublisherForm()
    return render(request, 'news/publisher_form.html', {'form': form})


# ── Subscriptions ─────────────────────────────────────────────────────────────

@login_required
def subscriptions(request):
    """Display all journalists and publishers; allow readers to subscribe or unsubscribe."""
    if request.user.role != 'reader':
        messages.error(request, 'Subscriptions are for readers only.')
        return redirect('article_list')
    journalists = CustomUser.objects.filter(role='journalist')
    publishers = Publisher.objects.all()
    return render(request, 'news/subscriptions.html', {
        'journalists': journalists,
        'publishers': publishers,
    })


@login_required
def toggle_journalist_subscription(request, pk):
    """Toggle the current reader's subscription to a specific journalist."""
    if request.user.role != 'reader':
        messages.error(request, 'Only readers can manage subscriptions.')
        return redirect('article_list')
    journalist = get_object_or_404(CustomUser, pk=pk, role='journalist')
    if journalist in request.user.subscribed_journalists.all():
        request.user.subscribed_journalists.remove(journalist)
        messages.success(request, f'Unsubscribed from {journalist.username}.')
    else:
        request.user.subscribed_journalists.add(journalist)
        messages.success(request, f'Subscribed to {journalist.username}.')
    return redirect('subscriptions')


@login_required
def toggle_publisher_subscription(request, pk):
    """Toggle the current reader's subscription to a specific publisher."""
    if request.user.role != 'reader':
        messages.error(request, 'Only readers can manage subscriptions.')
        return redirect('article_list')
    publisher = get_object_or_404(Publisher, pk=pk)
    if publisher in request.user.subscribed_publishers.all():
        request.user.subscribed_publishers.remove(publisher)
        messages.success(request, f'Unsubscribed from {publisher.name}.')
    else:
        request.user.subscribed_publishers.add(publisher)
        messages.success(request, f'Subscribed to {publisher.name}.')
    return redirect('subscriptions')


# ── Newsletters ───────────────────────────────────────────────────────────────

@login_required
def newsletter_list(request):
    """Display all newsletters to authenticated users."""
    newsletters = Newsletter.objects.select_related('author').prefetch_related('articles')
    return render(request, 'news/newsletter_list.html', {'newsletters': newsletters})


@login_required
def newsletter_detail(request, pk):
    """Display a single newsletter and its linked articles."""
    newsletter = get_object_or_404(Newsletter, pk=pk)
    return render(request, 'news/newsletter_detail.html', {'newsletter': newsletter})


@login_required
def newsletter_create(request):
    """Allow journalists and editors to create a new newsletter."""
    if request.user.role not in ('journalist', 'editor'):
        messages.error(request, 'Only journalists and editors can create newsletters.')
        return redirect('newsletter_list')
    if request.method == 'POST':
        form = NewsletterForm(request.POST)
        if form.is_valid():
            newsletter = form.save(commit=False)
            newsletter.author = request.user
            newsletter.save()
            form.save_m2m()
            messages.success(request, 'Newsletter created.')
            return redirect('newsletter_list')
    else:
        form = NewsletterForm()
    return render(request, 'news/newsletter_form.html', {'form': form, 'action': 'Create'})


@login_required
def newsletter_edit(request, pk):
    """Allow journalists (own newsletters) and editors (any newsletter) to edit a newsletter."""
    newsletter = get_object_or_404(Newsletter, pk=pk)
    if request.user.role not in ('journalist', 'editor'):
        messages.error(request, 'You do not have permission to edit newsletters.')
        return redirect('newsletter_list')
    if request.user.role == 'journalist' and newsletter.author != request.user:
        messages.error(request, 'You can only edit your own newsletters.')
        return redirect('newsletter_list')
    if request.method == 'POST':
        form = NewsletterForm(request.POST, instance=newsletter)
        if form.is_valid():
            form.save()
            messages.success(request, 'Newsletter updated.')
            return redirect('newsletter_detail', pk=newsletter.pk)
    else:
        form = NewsletterForm(instance=newsletter)
    return render(request, 'news/newsletter_form.html',
                  {'form': form, 'action': 'Edit', 'newsletter': newsletter})


@login_required
def newsletter_delete(request, pk):
    """Allow journalists (own newsletters) and editors (any newsletter) to delete a newsletter."""
    newsletter = get_object_or_404(Newsletter, pk=pk)
    if request.user.role not in ('journalist', 'editor'):
        messages.error(request, 'You do not have permission to delete newsletters.')
        return redirect('newsletter_list')
    if request.user.role == 'journalist' and newsletter.author != request.user:
        messages.error(request, 'You can only delete your own newsletters.')
        return redirect('newsletter_list')
    if request.method == 'POST':
        newsletter.delete()
        messages.success(request, 'Newsletter deleted.')
        return redirect('newsletter_list')
    return render(request, 'news/newsletter_confirm_delete.html', {'newsletter': newsletter})
