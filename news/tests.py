from django.test import TestCase, Client
from django.urls import reverse
from django.core import mail
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from .models import CustomUser, Publisher, Article, Newsletter


# ── Helpers ─────────────────────────────────────────────────────────────────

def make_user(username, role, password='pass1234!', publisher=None):
    return CustomUser.objects.create_user(
        username=username,
        email=f'{username}@test.com',
        password=password,
        role=role,
        publisher=publisher,
    )


def make_article(author, title='Test Article', approved=True, publisher=None):
    return Article.objects.create(
        title=title,
        content='Article content for testing purposes.',
        author=author,
        approved=approved,
        publisher=publisher,
    )


def make_newsletter(author, title='Test Newsletter'):
    return Newsletter.objects.create(
        title=title,
        description='Newsletter description.',
        author=author,
    )


# ── Model Tests ──────────────────────────────────────────────────────────────

class PublisherModelTest(TestCase):
    def setUp(self):
        self.publisher = Publisher.objects.create(name='Daily News', description='Top news.')

    def test_str_returns_name(self):
        self.assertEqual(str(self.publisher), 'Daily News')

    def test_created_at_set_automatically(self):
        self.assertIsNotNone(self.publisher.created_at)


class CustomUserModelTest(TestCase):
    def setUp(self):
        self.journalist = make_user('journalist1', 'journalist')
        self.reader = make_user('reader1', 'reader')
        self.publisher = Publisher.objects.create(name='Tech Times')

    def test_str_includes_role(self):
        self.assertIn('journalist', str(self.journalist))
        self.assertIn('reader', str(self.reader))

    def test_journalist_subscriptions_cleared_on_save(self):
        self.journalist.subscribed_publishers.add(self.publisher)
        self.journalist.save()
        self.assertEqual(self.journalist.subscribed_publishers.count(), 0)

    def test_reader_can_subscribe_to_publisher(self):
        self.reader.subscribed_publishers.add(self.publisher)
        self.assertIn(self.publisher, self.reader.subscribed_publishers.all())

    def test_reader_can_subscribe_to_journalist(self):
        self.reader.subscribed_journalists.add(self.journalist)
        self.assertIn(self.journalist, self.reader.subscribed_journalists.all())


class ArticleModelTest(TestCase):
    def setUp(self):
        self.journalist = make_user('jrn', 'journalist')
        self.article = make_article(self.journalist)

    def test_str_returns_title(self):
        self.assertEqual(str(self.article), 'Test Article')

    def test_approved_is_true_when_set(self):
        self.assertTrue(self.article.approved)

    def test_unapproved_article(self):
        article = make_article(self.journalist, approved=False)
        self.assertFalse(article.approved)

    def test_created_at_set_automatically(self):
        self.assertIsNotNone(self.article.created_at)


class NewsletterModelTest(TestCase):
    def setUp(self):
        self.journalist = make_user('jrn2', 'journalist')
        self.newsletter = make_newsletter(self.journalist)

    def test_str_returns_title(self):
        self.assertEqual(str(self.newsletter), 'Test Newsletter')

    def test_articles_can_be_added_to_newsletter(self):
        article = make_article(self.journalist)
        self.newsletter.articles.add(article)
        self.assertEqual(self.newsletter.articles.count(), 1)


# ── Authentication View Tests ─────────────────────────────────────────────────

class AuthViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_register_page_loads(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    def test_login_page_loads(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_register_creates_user(self):
        self.client.post(reverse('register'), {
            'username': 'newreader',
            'email': 'newreader@test.com',
            'role': 'reader',
            'password1': 'Str0ngPass!',
            'password2': 'Str0ngPass!',
        })
        self.assertEqual(CustomUser.objects.filter(username='newreader').count(), 1)

    def test_login_redirects_on_success(self):
        make_user('loginuser', 'reader')
        response = self.client.post(reverse('login'), {
            'username': 'loginuser',
            'password': 'pass1234!',
        })
        self.assertRedirects(response, reverse('article_list'))

    def test_login_fails_with_wrong_password(self):
        make_user('badpass', 'reader')
        response = self.client.post(reverse('login'), {
            'username': 'badpass',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)


# ── Role-Based Access Tests ────────────────────────────────────────────────────

class RoleAccessTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.reader = make_user('reader_u', 'reader')
        self.journalist = make_user('journalist_u', 'journalist')
        self.editor = make_user('editor_u', 'editor')

    def test_reader_cannot_create_article(self):
        self.client.force_login(self.reader)
        response = self.client.get(reverse('article_create'))
        self.assertRedirects(response, reverse('article_list'))

    def test_journalist_can_access_create_article(self):
        self.client.force_login(self.journalist)
        response = self.client.get(reverse('article_create'))
        self.assertEqual(response.status_code, 200)

    def test_reader_cannot_access_pending_queue(self):
        self.client.force_login(self.reader)
        response = self.client.get(reverse('article_pending'))
        self.assertRedirects(response, reverse('article_list'))

    def test_editor_can_access_pending_queue(self):
        self.client.force_login(self.editor)
        response = self.client.get(reverse('article_pending'))
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_redirected_to_login(self):
        response = self.client.get(reverse('article_list'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('article_list')}")


# ── Article Approval & Email Tests ────────────────────────────────────────────

class ArticleApprovalTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.journalist = make_user('jrn_appr', 'journalist')
        self.editor = make_user('ed_appr', 'editor')
        self.reader = make_user('rd_appr', 'reader')
        self.article = make_article(self.journalist, approved=False)

    def test_editor_can_approve_article(self):
        self.client.force_login(self.editor)
        self.client.post(reverse('article_approve', args=[self.article.pk]))
        self.article.refresh_from_db()
        self.assertTrue(self.article.approved)

    def test_non_editor_cannot_approve(self):
        self.client.force_login(self.journalist)
        self.client.post(reverse('article_approve', args=[self.article.pk]))
        self.article.refresh_from_db()
        self.assertFalse(self.article.approved)

    def test_approval_email_sent_to_subscribers(self):
        with self.settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            self.reader.subscribed_journalists.add(self.journalist)
            self.client.force_login(self.editor)
            self.client.post(reverse('article_approve', args=[self.article.pk]))
            self.assertEqual(len(mail.outbox), 1)
            self.assertIn(self.reader.email, mail.outbox[0].to)
            self.assertIn(self.article.title, mail.outbox[0].subject)

    def test_approval_email_not_sent_without_subscribers(self):
        with self.settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            self.client.force_login(self.editor)
            self.client.post(reverse('article_approve', args=[self.article.pk]))
            self.assertEqual(len(mail.outbox), 0)


# ── Newsletter Tests ─────────────────────────────────────────────────────────

class NewsletterTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.journalist = make_user('jrn_nl', 'journalist')
        self.reader = make_user('rd_nl', 'reader')
        self.article = make_article(self.journalist)

    def test_journalist_can_create_newsletter(self):
        self.client.force_login(self.journalist)
        self.client.post(reverse('newsletter_create'), {
            'title': 'Weekly Digest',
            'description': 'All the news.',
            'articles': [self.article.pk],
        })
        self.assertEqual(Newsletter.objects.filter(title='Weekly Digest').count(), 1)

    def test_reader_cannot_create_newsletter(self):
        self.client.force_login(self.reader)
        self.client.post(reverse('newsletter_create'), {
            'title': 'My Newsletter',
            'description': 'Test.',
        })
        self.assertRedirects(
            self.client.get(reverse('newsletter_create')),
            reverse('newsletter_list'),
        )

    def test_newsletter_list_accessible_to_readers(self):
        self.client.force_login(self.reader)
        response = self.client.get(reverse('newsletter_list'))
        self.assertEqual(response.status_code, 200)

    def test_newsletter_contains_articles(self):
        newsletter = make_newsletter(self.journalist)
        newsletter.articles.add(self.article)
        self.assertIn(self.article, newsletter.articles.all())


# ── REST API Authentication Tests ────────────────────────────────────────────

class APIAuthTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.journalist = make_user('api_jrn', 'journalist')
        self.reader = make_user('api_rdr', 'reader')

    def test_obtain_token_valid_credentials(self):
        response = self.client.post(reverse('api_token'), {
            'username': 'api_jrn',
            'password': 'pass1234!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['role'], 'journalist')

    def test_obtain_token_invalid_credentials(self):
        response = self.client.post(reverse('api_token'), {
            'username': 'api_jrn',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 401)

    def test_unauthenticated_cannot_list_articles(self):
        response = self.client.get(reverse('api_article_list'))
        self.assertEqual(response.status_code, 401)

    def test_authenticated_reader_can_list_articles(self):
        make_article(self.journalist)
        token, _ = Token.objects.get_or_create(user=self.reader)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = self.client.get(reverse('api_article_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_unapproved_articles_excluded_from_list(self):
        make_article(self.journalist, approved=False)
        token, _ = Token.objects.get_or_create(user=self.reader)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = self.client.get(reverse('api_article_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)


class APIJournalistTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.journalist = make_user('api_jrn2', 'journalist')
        self.reader = make_user('api_rdr2', 'reader')
        token, _ = Token.objects.get_or_create(user=self.journalist)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_journalist_can_create_article(self):
        response = self.client.post(reverse('api_article_list'), {
            'title': 'API Article',
            'content': 'Content here.',
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Article.objects.filter(title='API Article').count(), 1)

    def test_new_article_is_unapproved_by_default(self):
        self.client.post(reverse('api_article_list'), {
            'title': 'Unapproved API',
            'content': 'Content.',
        })
        article = Article.objects.get(title='Unapproved API')
        self.assertFalse(article.approved)

    def test_reader_cannot_create_article_via_api(self):
        reader_token, _ = Token.objects.get_or_create(user=self.reader)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {reader_token.key}')
        response = self.client.post(reverse('api_article_list'), {
            'title': 'Reader Article',
            'content': 'Content.',
        })
        self.assertEqual(response.status_code, 403)

    def test_journalist_can_update_own_article(self):
        article = make_article(self.journalist)
        response = self.client.put(reverse('api_article_detail', args=[article.pk]), {
            'title': 'Updated Title',
            'content': 'Updated content.',
        })
        self.assertEqual(response.status_code, 200)
        article.refresh_from_db()
        self.assertEqual(article.title, 'Updated Title')

    def test_journalist_cannot_update_others_article(self):
        other = make_user('other_jrn', 'journalist')
        article = make_article(other)
        response = self.client.put(reverse('api_article_detail', args=[article.pk]), {
            'title': 'Stolen Title',
            'content': 'Content.',
        })
        self.assertEqual(response.status_code, 403)

    def test_journalist_cannot_delete_others_article(self):
        other = make_user('other_jrn2', 'journalist')
        article = make_article(other)
        response = self.client.delete(reverse('api_article_detail', args=[article.pk]))
        self.assertEqual(response.status_code, 403)


class APIEditorTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.editor = make_user('api_ed2', 'editor')
        self.journalist = make_user('api_jrn3', 'journalist')
        token, _ = Token.objects.get_or_create(user=self.editor)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_editor_can_approve_article_via_api(self):
        article = make_article(self.journalist, approved=False)
        response = self.client.post(reverse('api_article_approve', args=[article.pk]))
        self.assertEqual(response.status_code, 200)
        article.refresh_from_db()
        self.assertTrue(article.approved)

    def test_editor_can_delete_article_via_api(self):
        article = make_article(self.journalist)
        response = self.client.delete(reverse('api_article_detail', args=[article.pk]))
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Article.objects.filter(pk=article.pk).count(), 0)

    def test_reader_cannot_approve_via_api(self):
        reader = make_user('rd_cant_appr', 'reader')
        reader_token, _ = Token.objects.get_or_create(user=reader)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {reader_token.key}')
        article = make_article(self.journalist, approved=False)
        response = self.client.post(reverse('api_article_approve', args=[article.pk]))
        self.assertEqual(response.status_code, 403)


class APISubscribedTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.journalist = make_user('sub_jrn', 'journalist')
        self.publisher = Publisher.objects.create(name='Sub Publisher')
        self.reader = make_user('sub_rdr', 'reader')
        token, _ = Token.objects.get_or_create(user=self.reader)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_reader_gets_subscribed_journalist_articles(self):
        self.reader.subscribed_journalists.add(self.journalist)
        make_article(self.journalist)
        response = self.client.get(reverse('api_article_subscribed'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_reader_does_not_get_unsubscribed_articles(self):
        other = make_user('other_jrn3', 'journalist')
        make_article(other)
        response = self.client.get(reverse('api_article_subscribed'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_reader_gets_subscribed_publisher_articles(self):
        self.reader.subscribed_publishers.add(self.publisher)
        make_article(self.journalist, publisher=self.publisher)
        response = self.client.get(reverse('api_article_subscribed'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_journalist_cannot_access_subscribed_endpoint(self):
        journalist_token, _ = Token.objects.get_or_create(user=self.journalist)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {journalist_token.key}')
        response = self.client.get(reverse('api_article_subscribed'))
        self.assertEqual(response.status_code, 403)


class APIArticleDetailTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.journalist = make_user('det_jrn', 'journalist')
        self.reader = make_user('det_rdr', 'reader')
        self.article = make_article(self.journalist)
        token, _ = Token.objects.get_or_create(user=self.reader)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_reader_can_retrieve_single_article(self):
        response = self.client.get(reverse('api_article_detail', args=[self.article.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['title'], self.article.title)

    def test_returns_404_for_nonexistent_article(self):
        response = self.client.get(reverse('api_article_detail', args=[9999]))
        self.assertEqual(response.status_code, 404)


class NewsletterAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.journalist = make_user('nl_jrn', 'journalist')
        self.reader = make_user('nl_rdr', 'reader')
        self.newsletter = make_newsletter(self.journalist)
        token, _ = Token.objects.get_or_create(user=self.reader)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_reader_can_list_newsletters(self):
        response = self.client.get(reverse('api_newsletter_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_newsletter_response_contains_title(self):
        response = self.client.get(reverse('api_newsletter_list'))
        self.assertEqual(response.data[0]['title'], self.newsletter.title)


# ── My Articles View Tests ────────────────────────────────────────────────────

class MyArticlesTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.journalist = make_user('my_jrn', 'journalist')
        self.reader = make_user('my_rdr', 'reader')

    def test_journalist_can_access_my_articles(self):
        self.client.force_login(self.journalist)
        response = self.client.get(reverse('my_articles'))
        self.assertEqual(response.status_code, 200)

    def test_my_articles_shows_own_pending_article(self):
        article = make_article(self.journalist, title='Pending One', approved=False)
        self.client.force_login(self.journalist)
        response = self.client.get(reverse('my_articles'))
        self.assertContains(response, 'Pending One')

    def test_my_articles_does_not_show_other_journalists_articles(self):
        other = make_user('other_jrn_ma', 'journalist')
        make_article(other, title='Other Article')
        self.client.force_login(self.journalist)
        response = self.client.get(reverse('my_articles'))
        self.assertNotContains(response, 'Other Article')

    def test_reader_cannot_access_my_articles(self):
        self.client.force_login(self.reader)
        response = self.client.get(reverse('my_articles'))
        self.assertRedirects(response, reverse('article_list'))

    def test_journalist_can_edit_own_article(self):
        article = make_article(self.journalist, title='Editable')
        self.client.force_login(self.journalist)
        response = self.client.post(
            reverse('article_edit', args=[article.pk]),
            {'title': 'Edited Title', 'content': 'New content.'},
        )
        article.refresh_from_db()
        self.assertEqual(article.title, 'Edited Title')

    def test_journalist_cannot_edit_others_article(self):
        other = make_user('other_jrn_edit', 'journalist')
        article = make_article(other, title='Not Mine')
        self.client.force_login(self.journalist)
        response = self.client.post(
            reverse('article_edit', args=[article.pk]),
            {'title': 'Stolen', 'content': 'Content.'},
        )
        article.refresh_from_db()
        self.assertEqual(article.title, 'Not Mine')

    def test_journalist_can_delete_own_article(self):
        article = make_article(self.journalist, title='To Delete')
        self.client.force_login(self.journalist)
        self.client.post(reverse('article_delete', args=[article.pk]))
        self.assertEqual(Article.objects.filter(pk=article.pk).count(), 0)


# ── Publisher Create Tests ────────────────────────────────────────────────────

class PublisherCreateTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.editor = make_user('pub_ed', 'editor')
        self.journalist = make_user('pub_jrn', 'journalist')

    def test_editor_can_access_publisher_create(self):
        self.client.force_login(self.editor)
        response = self.client.get(reverse('publisher_create'))
        self.assertEqual(response.status_code, 200)

    def test_editor_can_create_publisher(self):
        self.client.force_login(self.editor)
        self.client.post(reverse('publisher_create'), {
            'name': 'New Publisher',
            'description': 'A brand new publisher.',
        })
        self.assertEqual(Publisher.objects.filter(name='New Publisher').count(), 1)

    def test_journalist_cannot_create_publisher(self):
        self.client.force_login(self.journalist)
        response = self.client.get(reverse('publisher_create'))
        self.assertRedirects(response, reverse('article_list'))

    def test_duplicate_publisher_name_rejected(self):
        Publisher.objects.create(name='Existing Publisher')
        self.client.force_login(self.editor)
        response = self.client.post(reverse('publisher_create'), {
            'name': 'Existing Publisher',
            'description': 'Duplicate.',
        })
        self.assertEqual(Publisher.objects.filter(name='Existing Publisher').count(), 1)


# ── Subscription Tests ────────────────────────────────────────────────────────

class SubscriptionTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.reader = make_user('sub_reader', 'reader')
        self.journalist = make_user('sub_journalist', 'journalist')
        self.publisher = Publisher.objects.create(name='Sub Test Publisher')

    def test_reader_can_access_subscriptions_page(self):
        self.client.force_login(self.reader)
        response = self.client.get(reverse('subscriptions'))
        self.assertEqual(response.status_code, 200)

    def test_non_reader_cannot_access_subscriptions(self):
        self.client.force_login(self.journalist)
        response = self.client.get(reverse('subscriptions'))
        self.assertRedirects(response, reverse('article_list'))

    def test_reader_can_subscribe_to_journalist(self):
        self.client.force_login(self.reader)
        self.client.post(
            reverse('toggle_journalist_subscription', args=[self.journalist.pk])
        )
        self.assertIn(self.journalist, self.reader.subscribed_journalists.all())

    def test_reader_can_unsubscribe_from_journalist(self):
        self.reader.subscribed_journalists.add(self.journalist)
        self.client.force_login(self.reader)
        self.client.post(
            reverse('toggle_journalist_subscription', args=[self.journalist.pk])
        )
        self.assertNotIn(self.journalist, self.reader.subscribed_journalists.all())

    def test_reader_can_subscribe_to_publisher(self):
        self.client.force_login(self.reader)
        self.client.post(
            reverse('toggle_publisher_subscription', args=[self.publisher.pk])
        )
        self.assertIn(self.publisher, self.reader.subscribed_publishers.all())

    def test_reader_can_unsubscribe_from_publisher(self):
        self.reader.subscribed_publishers.add(self.publisher)
        self.client.force_login(self.reader)
        self.client.post(
            reverse('toggle_publisher_subscription', args=[self.publisher.pk])
        )
        self.assertNotIn(self.publisher, self.reader.subscribed_publishers.all())

    def test_journalist_cannot_toggle_journalist_subscription(self):
        other_jrn = make_user('other_sub_jrn', 'journalist')
        self.client.force_login(self.journalist)
        response = self.client.post(
            reverse('toggle_journalist_subscription', args=[other_jrn.pk])
        )
        self.assertRedirects(response, reverse('article_list'))


# ── Editor Article Management Tests ──────────────────────────────────────────

class EditorArticleManagementTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.editor = make_user('ed_mgmt', 'editor')
        self.journalist = make_user('jrn_mgmt', 'journalist')
        self.article = make_article(self.journalist, approved=False)

    def test_editor_can_edit_any_article(self):
        self.client.force_login(self.editor)
        self.client.post(
            reverse('article_edit', args=[self.article.pk]),
            {'title': 'Editor Changed', 'content': 'New content.'},
        )
        self.article.refresh_from_db()
        self.assertEqual(self.article.title, 'Editor Changed')

    def test_editor_can_delete_any_article(self):
        self.client.force_login(self.editor)
        self.client.post(reverse('article_delete', args=[self.article.pk]))
        self.assertEqual(Article.objects.filter(pk=self.article.pk).count(), 0)

    def test_pending_page_shows_edit_link(self):
        self.client.force_login(self.editor)
        response = self.client.get(reverse('article_pending'))
        self.assertContains(response, reverse('article_edit', args=[self.article.pk]))
