# Search Index Engine

Version: v1.0  
Status: Active

## Scope
Implements Phase 7 full-text retrieval for controlled documents.

## Components

- `DocumentSearchIndex` materialized index table
- PDF text extraction pipeline (`pypdf`)
- OCR fallback pipeline (`pdf2image` + `pytesseract`, configurable)
- Clause tokenizer and indexed clause storage
- PostgreSQL `SearchVector` + GIN index for ranked retrieval

## Data Model

Primary table: `documents_documentsearchindex`

Core fields:
- `document` (1:1)
- `document_version` (indexed source revision)
- `extracted_text`
- `ocr_text`
- `clause_text`
- `indexed_clauses` (JSON)
- `combined_text`
- `search_vector` (`tsvector`)
- `index_status`, `indexed_at`, `error_message`

## Indexing Triggers

1. Automatic: `post_save` signal on `DocumentVersion`
2. Manual API: `POST /api/documents/search-index/rebuild/`
3. Manual CLI: `python manage.py rebuild_documents_search_index`

## Operational Commands

- Rebuild all:
  - `python manage.py rebuild_documents_search_index --force`
- Rebuild one:
  - `python manage.py rebuild_documents_search_index --document-id 42 --force`

## OCR Controls

Environment variables:
- `DOCUMENT_OCR_ENABLED` (`True`/`False`)
- `DOCUMENT_OCR_LANG` (default `eng`)
- `DOCUMENT_OCR_DPI` (default `220`)
- `DOCUMENT_OCR_MAX_PAGES` (default `20`)
