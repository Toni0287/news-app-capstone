# News Application

A Django news platform with three kinds of user:

- **Journalists** write articles and newsletters.
- **Editors** review and approve articles before readers can see them.
- **Readers** subscribe to publishers and journalists, and are emailed when a new article they follow is approved.

The app also has a REST API (Django REST Framework) with token authentication.

## Secrets and configuration

No secrets are stored in this repository. The app reads its settings from environment variables, or from a `.env` file in the project root:

| Variable | Purpose | Example |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | **Required.** Django's secret key | a generated key (see below) |
| `DJANGO_DEBUG` | `True` for development, `False` otherwise | `True` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames the app may be served on | `localhost,127.0.0.1` |

To create your own `.env`:

1. Copy the template:
   ```bash
   cp .env.example .env
   ```
2. Generate a secret key (after installing the requirements below):
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```
3. Paste the key into `.env` as the value of `DJANGO_SECRET_KEY`.

Never commit `.env`; it is already listed in `.gitignore`.

## Run with a virtual environment (venv)

Requires Python 3.12 or newer.

1. Clone the repository and go into it:
   ```bash
   git clone <repository-url>
   cd news-capstone
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate        # Linux / macOS
   venv\Scripts\activate           # Windows
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create your `.env` file as described in [Secrets and configuration](#secrets-and-configuration).
5. Create the database tables:
   ```bash
   python manage.py migrate
   ```
6. (Optional) Create an admin account for the Django admin at `/admin/`:
   ```bash
   python manage.py createsuperuser
   ```
7. Start the development server:
   ```bash
   python manage.py runserver
   ```
8. Open http://127.0.0.1:8000/ and register a reader, journalist or editor account.

To run the tests:
```bash
python manage.py test
```

## Run with Docker

1. Build the image from the project root:
   ```bash
   docker build -t news-app .
   ```
2. Run a container, passing in your own secret key:
   ```bash
   docker run -p 8000:8000 -e DJANGO_SECRET_KEY="your-generated-key" news-app
   ```
   If you have already created a `.env` file, you can pass that instead:
   ```bash
   docker run -p 8000:8000 --env-file .env news-app
   ```
3. Open http://localhost:8000/.

The container applies migrations when it starts and serves the app with Gunicorn. Static files are served by WhiteNoise, so `DJANGO_DEBUG` can stay `False`.

**Docker Playground or another host:** the app only accepts `localhost` and `127.0.0.1` by default. Allow the playground's hostname (or any host, for testing only) with `DJANGO_ALLOWED_HOSTS`:
```bash
docker run -p 8000:8000 -e DJANGO_SECRET_KEY="your-generated-key" -e DJANGO_ALLOWED_HOSTS="*" news-app
```

To create an admin account inside a running container:
```bash
docker exec -it <container-id> python manage.py createsuperuser
```

The SQLite database lives inside the container, so data is lost when the container is removed.

## Documentation

HTML documentation generated with Sphinx is in `docs/_build/html`. Open `docs/_build/html/index.html` in a browser.

To rebuild it after changing docstrings:
```bash
pip install -r docs/requirements.txt
cd docs
make clean
make html
```
If `make` is not installed, use `sphinx-build -M clean . _build` and `sphinx-build -M html . _build` instead.

## REST API

| Endpoint | Method | Description |
| --- | --- | --- |
| `/api/token/` | POST | Get a token with `username` and `password` |
| `/api/articles/` | GET, POST | List approved articles; journalists can create one |
| `/api/articles/subscribed/` | GET | Articles from the reader's subscriptions |
| `/api/articles/<id>/` | GET, PUT, DELETE | View, update or delete an article |
| `/api/articles/<id>/approve/` | POST | Approve an article (editors only) |
| `/api/newsletters/` | GET | List newsletters |

Send the token in the `Authorization: Token <your-token>` header.
