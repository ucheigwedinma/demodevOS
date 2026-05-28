# Metadata Query Layer

Version: v1.0  
Status: Active

## Scope
Implements structured retrieval filters and ranked full-text search for document discovery.

## Structured Filtering

Endpoint: `GET /api/documents/records/`

Supported filters:
- `project`
- `land`
- `unit`
- `vendor`
- `client`
- `category` (maps to `DocumentType.category_code`)
- `created_from`
- `created_to`
- `status`

Also supported:
- `search` (title/document number)
- `ordering`

## Full-Text + Clause Search

Endpoint: `GET /api/documents/search/`

Query params:
- `q`: full-text query (ranked when PostgreSQL is active)
- `clause`: clause-level contains match
- all structured filters from metadata endpoint

Result includes:
- metadata projection
- `search_rank`
- `snippet`
- `matching_clauses`

## Search Index Monitoring

Endpoint: `GET /api/documents/search-index/`

Fields include:
- `index_status`
- `indexed_at`
- `error_message`
- linked document/version IDs
