# Iron House OS MVP Launch Checklist

## Objective

Get Iron House OS running as a usable web app quickly.

## MVP Modules To Verify

1. Dashboard
   - Replace placeholder with basic cards.
   - Show active projects, tendering projects, RFQs, suppliers, and next actions.

2. Projects
   - Create project.
   - Open project detail.
   - Update project status.
   - Archive project.

3. Suppliers
   - Create supplier.
   - Add estimating contact.
   - Search/filter suppliers.
   - Update supplier notes/category/service area.

4. RFQs
   - Create RFQ package.
   - Select supplier recipients.
   - Register required documents.
   - Check readiness.
   - Generate supplier RFQ draft.

5. Estimating
   - Add line items.
   - Use production defaults.
   - Calculate bid summary.
   - Export workbook.

6. Quotes
   - Compare quotes through backend endpoint.
   - Connect UI after dashboard is complete.

## Local Launch

From repo root:

```bash
docker compose up --build
```

Expected local URLs:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Backend Checks

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
ruff check .
uvicorn app.main:app --reload
```

## Frontend Checks

```bash
cd frontend
npm install
npm run build
npm run lint
npm run dev
```

## Known Fast-Fix Items

- Add dashboard page in `frontend/src/pages/DashboardPage.tsx`.
- Route `/dashboard` to dashboard page instead of placeholder.
- Add quote comparison UI.
- Add disposal and vendor quote inputs to Estimating page.
- Add focused workbook tests.
- Confirm backend dependency pins after local install.

## Deployment Target

For fastest MVP deployment:

- Use managed Postgres.
- Deploy backend as FastAPI service.
- Deploy frontend as static Vite app.
- Set `VITE_API_BASE_URL` to backend `/api/v1` URL.
- Keep Gmail/Drive automation disabled until manual workflows are stable.
