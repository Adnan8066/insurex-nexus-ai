# InsureX Nexus AI frontend

React and Vite client for the InsureX insurance claims application.

## Run locally

1. Install Node.js and Python dependencies.
2. In `frontend`, copy `.env.example` to `.env.local`, run `npm install`, and then `npm run dev`.
3. In `backend/django_backend`, copy `.env.example` to `.env`, run `python manage.py migrate`, and start Django with `python manage.py runserver`.
4. Open <http://localhost:3000>. The frontend calls the API at <http://127.0.0.1:8000/api/v1> by default. Override it with `VITE_API_BASE_URL` in `frontend/.env.local` when needed.

The local database is intentionally empty after setup. To load the bundled demo scenarios, run `python manage.py import_project_datasets` from `backend/django_backend`.

## Quality checks

```sh
npm run lint
npm run build
```

Backend checks, schema validation, and tests are run from `backend/django_backend`:

```sh
python manage.py check
python manage.py spectacular --validate --file openapi-schema.yml
python manage.py test
```

## Production configuration

Set `DEBUG=False`, a generated `SECRET_KEY`, real `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, and `CSRF_TRUSTED_ORIGINS`. Configure the database, HTTPS termination, email, and media storage for the target environment. See `backend/django_backend/.env.example` for the supported settings. Never use the local development secret in production.

The production defaults enable HTTPS redirects and one-year HSTS with subdomains and preload. Use them only after the production domain and every subdomain are served exclusively over HTTPS; override the HSTS environment settings if that is not true.
