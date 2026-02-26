# Web3 Job Monitor (Personal Dashboard)

## Features
- 5 sources: LinkedIn, CryptoJobsList, Web3.career, Wellfound, Remote3
- Crawl every 8 hours (GitHub Actions)
- PostgreSQL storage with dedupe
- High-priority scoring (`>=70`)
- Discord single notifications + run digest
- FastAPI backend + Next.js frontend

## Quick start (Docker)
```bash
cd web3-job-monitor
docker compose up --build
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`
- Default login: `admin / change-me`

## Local backend run
```bash
cd backend
cp .env.example .env
pip install -e .[dev]
uvicorn app.main:app --reload
```

## Local frontend run
```bash
cd frontend
npm install
npm run dev
```

## API
- `POST /api/v1/auth/login`
- `GET /api/v1/jobs`
- `GET /api/v1/jobs/{id}`
- `GET /api/v1/runs`
- `GET /api/v1/sources`
- `PATCH /api/v1/sources/{id}`
- `GET /api/v1/settings/scoring`
- `PUT /api/v1/settings/scoring`
- `GET /api/v1/settings/notifications`
- `PUT /api/v1/settings/notifications`
- `POST /api/v1/crawl/trigger`
- `GET /health`

## GitHub Actions
Workflow file: `.github/workflows/crawl.yml`

Set repository secrets:
- `DATABASE_URL`
- `AUTH_USERNAME`
- `AUTH_PASSWORD`
- `JWT_SECRET`
- `DISCORD_BOT_TOKEN`
- `DISCORD_CHANNEL_ID`
- `DISCORD_WEBHOOK_URL`
