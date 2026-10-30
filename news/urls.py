from django.urls import path
from . import views, api_views

urlpatterns = [
    # Auth
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Articles (web)
    path('', views.article_list, name='article_list'),
    path('articles/', views.article_list, name='article_list'),
    path('articles/create/', views.article_create, name='article_create'),
    path('articles/pending/', views.article_pending, name='article_pending'),
    path('articles/mine/', views.my_articles, name='my_articles'),
    path('articles/<int:pk>/', views.article_detail, name='article_detail'),
    path('articles/<int:pk>/edit/', views.article_edit, name='article_edit'),
    path('articles/<int:pk>/delete/', views.article_delete, name='article_delete'),
    path('articles/<int:pk>/approve/', views.article_approve, name='article_approve'),

    # Publishers (web)
    path('publishers/create/', views.publisher_create, name='publisher_create'),

    # Subscriptions (web)
    path('subscriptions/', views.subscriptions, name='subscriptions'),
    path('subscriptions/journalist/<int:pk>/toggle/', views.toggle_journalist_subscription,
         name='toggle_journalist_subscription'),
    path('subscriptions/publisher/<int:pk>/toggle/', views.toggle_publisher_subscription,
         name='toggle_publisher_subscription'),

    # Newsletters (web)
    path('newsletters/', views.newsletter_list, name='newsletter_list'),
    path('newsletters/create/', views.newsletter_create, name='newsletter_create'),
    path('newsletters/<int:pk>/', views.newsletter_detail, name='newsletter_detail'),
    path('newsletters/<int:pk>/edit/', views.newsletter_edit, name='newsletter_edit'),
    path('newsletters/<int:pk>/delete/', views.newsletter_delete, name='newsletter_delete'),

    # RESTful API
    path('api/token/', api_views.api_token, name='api_token'),
    path('api/articles/', api_views.api_article_list, name='api_article_list'),
    path('api/articles/subscribed/', api_views.api_article_subscribed, name='api_article_subscribed'),
    path('api/articles/<int:pk>/', api_views.api_article_detail, name='api_article_detail'),
    path('api/articles/<int:pk>/approve/', api_views.api_article_approve, name='api_article_approve'),
    path('api/newsletters/', api_views.api_newsletter_list, name='api_newsletter_list'),
]
