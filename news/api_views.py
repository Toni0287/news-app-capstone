from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate

from .models import Article, Newsletter
from .serializers import ArticleSerializer, ArticleCreateSerializer, NewsletterSerializer


def _is_journalist(user):
    return user.is_authenticated and user.role == 'journalist'


def _is_editor(user):
    return user.is_authenticated and user.role == 'editor'


# ── Token Auth endpoint ──────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def api_token(request):
    """Obtain an authentication token with username and password."""
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'role': user.role})


# ── Articles ─────────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def api_article_list(request):
    """
    GET  – Return all approved articles.
    POST – Create a new article (journalists only).
    """
    if request.method == 'GET':
        articles = Article.objects.filter(approved=True).select_related('author', 'publisher')
        serializer = ArticleSerializer(articles, many=True)
        return Response(serializer.data)

    # POST
    if not _is_journalist(request.user):
        return Response(
            {'error': 'Only journalists can create articles.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    serializer = ArticleCreateSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(author=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_article_subscribed(request):
    """Return only articles from the reader's subscribed publishers/journalists."""
    user = request.user
    if user.role != 'reader':
        return Response(
            {'error': 'Only readers have subscriptions.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    articles = Article.objects.filter(approved=True).filter(
        author__in=user.subscribed_journalists.all()
    ) | Article.objects.filter(approved=True).filter(
        publisher__in=user.subscribed_publishers.all()
    )
    articles = articles.distinct().select_related('author', 'publisher')
    serializer = ArticleSerializer(articles, many=True)
    return Response(serializer.data)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def api_article_detail(request, pk):
    """
    GET    – Retrieve a single article.
    PUT    – Update an article (editors/journalists).
    DELETE – Delete an article (editors/journalists).
    """
    try:
        article = Article.objects.get(pk=pk)
    except Article.DoesNotExist:
        return Response({'error': 'Article not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = ArticleSerializer(article)
        return Response(serializer.data)

    if request.user.role not in ('journalist', 'editor'):
        return Response(
            {'error': 'Permission denied.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == 'PUT':
        # Journalists can only update their own articles
        if _is_journalist(request.user) and article.author != request.user:
            return Response(
                {'error': 'You can only edit your own articles.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ArticleCreateSerializer(article, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        if _is_journalist(request.user) and article.author != request.user:
            return Response(
                {'error': 'You can only delete your own articles.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        article.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_article_approve(request, pk):
    """Approve an article (editors only)."""
    if not _is_editor(request.user):
        return Response(
            {'error': 'Only editors can approve articles.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    try:
        article = Article.objects.get(pk=pk)
    except Article.DoesNotExist:
        return Response({'error': 'Article not found.'}, status=status.HTTP_404_NOT_FOUND)

    article.approved = True
    article.save()
    # Re-use the subscriber notification from views
    from .views import _notify_subscribers
    _notify_subscribers(article)
    return Response({'status': 'approved', 'article_id': article.pk})


# ── Newsletters ───────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_newsletter_list(request):
    newsletters = Newsletter.objects.select_related('author').prefetch_related('articles')
    serializer = NewsletterSerializer(newsletters, many=True)
    return Response(serializer.data)
