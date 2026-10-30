# News Application - production-style image (Gunicorn + WhiteNoise)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first so this layer is cached between code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Collect static files at build time. Settings need a secret key to load,
# so a throwaway one is used here only; the real key is passed at run time.
RUN DJANGO_SECRET_KEY=collectstatic-build-only python manage.py collectstatic --noinput

EXPOSE 8000

# Apply migrations on start-up, then serve the app with Gunicorn
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn newsapp.wsgi:application --bind 0.0.0.0:8000 --workers 3"]
