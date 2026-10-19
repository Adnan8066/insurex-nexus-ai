# Deploying the Django API

The frontend is already on Vercel. The Django API is configured for Render in the repository-root `render.yaml` Blueprint.

## Before deploying

The API needs a PostgreSQL database. `DATABASE_URL` is intentionally a secret entered in Render, not stored in this repository. Choose a database that will keep your data for as long as you need it. Render's free PostgreSQL databases expire after 30 days, so use one only for a temporary demo.

## Deploy

1. Push the backend deployment changes to the GitHub repository.
2. In Render, create a new Blueprint and connect `Adnan8066/insurex-nexus-ai`.
3. When prompted for `DATABASE_URL`, enter the connection URL from your PostgreSQL provider. Render will generate `SECRET_KEY` and run migrations during the build.
4. Wait until the service is live. Check `https://<your-render-service>.onrender.com/api/health/`; it should return `{"status":"ok"}`.
5. In Vercel, open the `frontend` project's Environment Variables and set `VITE_API_BASE_URL` to `https://<your-render-service>.onrender.com/api/v1`. Redeploy the frontend so the build includes the new value.
6. Create the first administrator from the Render Shell with `python backend/django_backend/manage.py createsuperuser`.

## Uploaded files

Render's free web service has an ephemeral filesystem. Uploaded claim, vehicle, and policy files need persistent object storage or a persistent disk before they are relied on in production.
