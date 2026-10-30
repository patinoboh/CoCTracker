# CoCTracker

A small Django application for tracking Clash of Clans upgrades across multiple
accounts and villages.

## Local setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/admin/` to create game accounts, villages, and
upgrade options. The dashboard is available at `http://127.0.0.1:8000/`.

Create a dedicated token for Apple Shortcuts after creating a user:

```bash
python manage.py create_shortcut_token <username> "iPhone"
```

Copy the printed token into the Shortcut's `Authorization` header as
`Bearer <token>`. Tokens are hashed in the database and can be revoked in the
admin interface.

The JSON endpoints under `/api/shortcut/` are shaped for Apple Shortcuts:
accounts, villages, and upgrade options return an `items` array containing
stable IDs, titles, and optional subtitles.

The browser dashboard uses a Django session. Shortcut endpoints accept either
that session during local testing or a device-specific bearer token.

Each account has an **Import game export JSON** form on the dashboard. The
original export is preserved as a versioned snapshot, and level-shaped records
are extracted for future synchronization logic. The same operation is
available to Shortcuts with:

```text
POST /api/shortcut/accounts/<account_id>/import
Authorization: Bearer <token>
Content-Type: application/json
```

## Server deployment

The project is ready for a managed Python host. It uses `DJANGO_SECRET_KEY`,
`DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, and
`DATABASE_URL` from the environment,
and serves production assets through WhiteNoise. `render.yaml` describes a
Render web service and PostgreSQL database; review the service name and domain
before applying it. Never commit production secrets or the production database
URL.
