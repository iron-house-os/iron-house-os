# Drawing intelligence

Build 206 replaces the manual-only drawing classifier with project-scoped civil PDF ingestion and evidence-backed analysis.

## Workflow

1. Select a project and upload a PDF drawing set.
2. IHOS stores the source through the document library and retains its SHA-256 hash, storage URI, original filename, byte size, and page count.
3. Embedded PDF text is extracted page by page. Pages without embedded text are marked for OCR.
4. Explicit civil measurements are surfaced as quantity candidates with page numbers, source excerpts, confidence, and a mandatory verification flag.
5. Constructability language and municipal-standard references are surfaced as review items.

Analysis reports persist in the source document's metadata and can be listed by project, read by document ID, or regenerated from the immutable stored PDF.

## API

- `POST /api/v1/drawing-intelligence/ingest` accepts a project ID and PDF upload.
- `GET /api/v1/drawing-intelligence/projects/{project_id}` lists persisted project analyses.
- `GET /api/v1/drawing-intelligence/{document_id}` returns one persisted report.
- `POST /api/v1/drawing-intelligence/{document_id}/reanalyze` regenerates a report from the stored source.
- `POST /api/v1/drawing-intelligence/analyze` remains available for legacy manual sheet metadata analysis.

## Safety and interpretation

- Quantity results are candidates, not approved takeoff quantities.
- Every candidate includes `requires_verification: true` and page-level evidence.
- Municipal findings identify missing, ambiguous, or conflicting references; they do not claim code or standards compliance.
- Constructability findings are keyword-supported review prompts, not engineering conclusions.
- The document audit stream records ingestion with source hash, page count, extraction status, and candidate count.

## Known limitations

- Image-only PDFs require a future OCR provider; this build reports `ocr_required` and does not guess.
- Text extraction does not interpret geometry, scale bars, vector layers, or graphical dimensions.
- Quantity detection is intentionally conservative and limited to explicit text measurements or counts.
- Municipal standards editions and requirements are not downloaded or validated.
- Reports are stored in document JSON metadata until a dedicated analysis table is justified.
