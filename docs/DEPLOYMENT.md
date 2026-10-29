# Deploying for free

| Part | Service | Free plan notes |
| --- | --- | --- |
| Frontend (React) | [Vercel](https://vercel.com) | Always on |
| API (Django) | [Render](https://render.com) | Sleeps after 15 minutes idle; the next request takes 30–60 s |
| Database (PostgreSQL) | [Neon](https://neon.tech) | 0.5 GB, does not expire (Render's free Postgres is deleted after 30 days) |

The Django API cannot run on Vercel: its machine-learning libraries exceed Vercel's function size limit, and Vercel has no persistent database.

## 1. Push the code to GitHub

```powershell
git pull
git add -A
git commit -m "Prepare free deployment"
git push
```

## 2. Create the database (Neon)

1. Sign up at neon.tech and create a project (any name, region closest to your users).
2. On the project dashboard, copy the **connection string**. It looks like
   `postgresql://user:password@ep-xxx.region.aws.neon.tech/neondb?sslmode=require`.

## 3. Deploy the API (Render)

1. Sign up at render.com with your GitHub account.
2. Choose **New → Blueprint** and select this repository. Render reads `render.yaml`.
3. Fill in the values it asks for:
   - `DATABASE_URL`: the Neon connection string.
   - `DJANGO_SUPERUSER_EMAIL`: the email you will log in with as admin.
   - `DJANGO_SUPERUSER_PASSWORD`: a strong password for that admin.
4. Click **Apply**. The build installs packages, runs migrations, and creates the admin account (`manage.py ensure_admin`). The first build takes about 10 minutes.
5. When the service shows **Live**, open `https://<your-service>.onrender.com/api/health/`. It should return `{"status":"ok"}`.

`render.yaml` allows requests from `https://frontend-omega-murex-45.vercel.app`. If your Vercel address is different, change `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, and `FRONTEND_URL` under the service's **Environment** tab and redeploy.

## 4. Deploy the frontend (Vercel)

1. Sign up at vercel.com with your GitHub account and choose **Add New → Project**, then import this repository.
2. Set **Root Directory** to `frontend`. Vercel detects Vite automatically.
3. Under **Environment Variables**, add `VITE_API_BASE_URL` = `https://<your-service>.onrender.com/api/v1`.
4. Click **Deploy**. Vite reads this variable at build time, so redeploy whenever you change it.

## 5. First login and test data

1. Open the Vercel site and log in with the admin email and password from step 3.
2. In **User menu → Administration → User management**, create at least one **employee**. Policy requests and new claims are assigned automatically to employees.
3. Register a customer on the sign-up page, add a vehicle, request a policy, and check that it appears for the employee.

Optional demo data: run the import from your own computer against the Neon database.

```powershell
cd backend/django_backend
$env:DATABASE_URL = "postgresql://...neon connection string..."
python manage.py import_project_datasets
Remove-Item Env:DATABASE_URL   # back to the local SQLite database
```

## Free-plan limitations

- **Cold starts:** open the site a minute before a demo so the API wakes up.
- **Uploaded files are temporary:** Render's free filesystem is wiped on every restart or deploy, so claim photos and documents disappear. Use persistent storage (for example a paid Render disk or S3-compatible storage) before relying on uploads.
- **RL routing advice is off:** the PPO model files are not in the repository. New claims are assigned to the least-busy employee instead.
