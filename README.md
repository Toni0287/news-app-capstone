# News Application

A Django news platform with three kinds of user:

- **Journalists** write articles and newsletters.
- **Editors** review and approve articles before readers can see them.
- **Readers** subscribe to publishers and journalists, and are emailed when a new article they follow is approved.

The app also has a REST API (Django REST Framework) with token authentication. It stores its data in **MariaDB**.

There are two ways to run it. Each section below is complete on its own, so follow only one:

- [Option A: Run with a virtual environment (venv) and MariaDB](#option-a-run-with-a-virtual-environment-venv-and-mariadb)
- [Option B: Run with Docker](#option-b-run-with-docker) (MariaDB is included, nothing else to install)

No secrets are stored in this repository. Each option shows you how to create your own `.env` file with your own secret key and database password. Never commit `.env`; it is already listed in `.gitignore`.

---

## Option A: Run with a virtual environment (venv) and MariaDB

### Prerequisites

- Python 3.12 or newer
- Git
- MariaDB 10.6 or newer (tested with 11.4), installed and running:
  - **Windows / macOS:** download it from https://mariadb.org/download/ (on macOS you can also run `brew install mariadb` and then `brew services start mariadb`)
  - **Ubuntu / WSL:**
    ```bash
    sudo apt update && sudo apt install mariadb-server
    sudo service mariadb start
    ```

### 1. Clone the project

```bash
git clone https://github.com/Toni0287/news-app-capstone.git
cd news-app-capstone
```

### 2. Create the MariaDB database and user

Open the MariaDB shell as the root (admin) user:

- **Ubuntu / WSL:**
  ```bash
  sudo mariadb
  ```
- **Windows / macOS** (enter the root password you chose when installing MariaDB):
  ```bash
  mariadb -u root -p
  ```

At the `MariaDB [(none)]>` prompt, paste the following. Replace `choose-a-password` with a password of your own and keep a note of it for step 5:

```sql
CREATE DATABASE newsapp_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'newsapp_user'@'localhost' IDENTIFIED BY 'choose-a-password';
GRANT ALL PRIVILEGES ON newsapp_db.* TO 'newsapp_user'@'localhost';
-- Lets the test runner create and remove its own test database
GRANT ALL PRIVILEGES ON test_newsapp_db.* TO 'newsapp_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 3. Create and activate a virtual environment

```bash
python -m venv venv
```

Activate it:

- **Linux / macOS / WSL:** `source venv/bin/activate`
- **Windows (Command Prompt or PowerShell):** `venv\Scripts\activate`

### 4. Install the dependencies

```bash
pip install -r requirements.txt
```

### 5. Create your `.env` file and add your credentials

1. Copy the template:
   ```bash
   cp .env.example .env          # Linux / macOS / WSL
   copy .env.example .env        # Windows
   ```
2. Generate a secret key:
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```
3. Open `.env` in a text editor and update these lines:
   - `DJANGO_SECRET_KEY=` the key you just generated
   - `DB_PASSWORD=` the MariaDB password you chose in step 2

   Leave `DB_NAME=newsapp_db`, `DB_USER=newsapp_user`, `DB_HOST=127.0.0.1` and `DB_PORT=3306` as they are, unless you used different values in step 2. `DB_ROOT_PASSWORD` is only used by Docker and can be ignored here.

### 6. Create the database tables

```bash
python manage.py migrate
```

### 7. (Optional) Create an admin account

For the Django admin at http://127.0.0.1:8000/admin/:

```bash
python manage.py createsuperuser
```

### 8. Start the server

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000/ and register a reader, journalist or editor account.

To run the tests (they use a separate `test_newsapp_db` database, created and removed automatically):

```bash
python manage.py test
```

---

## Option B: Run with Docker

Docker runs the app and its MariaDB database (MariaDB **11.4**, the official `mariadb:11.4` image) in two containers. You do not need Python or MariaDB installed.

### Prerequisites

- Git
- **Docker Desktop installed and running** (Windows and macOS): https://www.docker.com/products/docker-desktop/
  Start Docker Desktop and wait until it shows **Engine running** before you run any `docker` command. On Windows with WSL, also turn on **Settings → Resources → WSL integration** for your Linux distribution.
- On Linux without Docker Desktop: Docker Engine with the Compose plugin (https://docs.docker.com/engine/install/), with the Docker service running.

Check that Docker is ready:

```bash
docker compose version
```

### 1. Clone the project

```bash
git clone https://github.com/Toni0287/news-app-capstone.git
cd news-app-capstone
```

### 2. Create your `.env` file and add your credentials

1. Copy the template:
   ```bash
   cp .env.example .env          # Linux / macOS / WSL
   copy .env.example .env        # Windows
   ```
2. Generate a secret key (this uses Docker, so you do not need Python installed):
   ```bash
   docker run --rm python:3.12-slim python -c "import secrets; print(secrets.token_urlsafe(50))"
   ```
3. Open `.env` in a text editor and update these lines:
   - `DJANGO_SECRET_KEY=` the key you just generated
   - `DB_PASSWORD=` a password of your choice for the app's database user
   - `DB_ROOT_PASSWORD=` a different password of your choice for MariaDB's root user

   Docker creates the `newsapp_db` database and the `newsapp_user` user with these passwords the first time it starts. `DB_HOST` is set to the database container automatically, so leave it as it is.

### 3. Build and start the containers

```bash
docker compose up --build
```

The first run downloads the images and takes a few minutes. The app waits until MariaDB is ready, creates the database tables, then starts. When you see `Listening at: http://0.0.0.0:8000`, open http://localhost:8000/.

### 4. (Optional) Create an admin account

In a second terminal, from the same folder:

```bash
docker compose exec web python manage.py createsuperuser
```

### 5. Stop the app

Press `Ctrl + C`, then:

```bash
docker compose down
```

Your data is kept in a Docker volume and is still there next time you run `docker compose up`. To delete the database as well, run `docker compose down -v`.

**Docker Playground or another host:** the app only accepts `localhost` and `127.0.0.1` by default. Add the host's name to `DJANGO_ALLOWED_HOSTS` in `.env` (or use `*` for testing only), then run `docker compose up --build` again.

---

## Configuration reference

All settings are read from `.env`:

| Variable | Purpose | Default in `.env.example` |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | **Required.** Django's secret key | placeholder, replace it |
| `DJANGO_DEBUG` | `True` for development, `False` otherwise | `True` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames the app may be served on | `localhost,127.0.0.1` |
| `DB_NAME` | MariaDB database name | `newsapp_db` |
| `DB_USER` | MariaDB user | `newsapp_user` |
| `DB_PASSWORD` | **Required.** Password for `DB_USER` | placeholder, replace it |
| `DB_HOST` | MariaDB host (Docker sets this to `db`) | `127.0.0.1` |
| `DB_PORT` | MariaDB port | `3306` |
| `DB_ROOT_PASSWORD` | Docker only: MariaDB root password | placeholder, replace it |

## Documentation

HTML documentation generated with Sphinx is in `docs/_build/html`. Open `docs/_build/html/index.html` in a browser.

To rebuild it after changing docstrings (with the venv from Option A activated):

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
