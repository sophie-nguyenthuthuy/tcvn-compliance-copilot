# API reference

The API is OpenAPI 3.1 documented at `/docs` (Swagger) and `/redoc` when the
service is not running in `production`. The complete schema is at
`/openapi.json`.

## Authentication

All endpoints other than `/healthz`, `/readyz`, `/metrics`, `/auth/*`,
`/standards/*` (read-only) require a bearer token in the `Authorization`
header:

```
Authorization: Bearer <access_token>
```

Tokens are issued by `POST /auth/login`. Access tokens TTL = 60 min;
refresh tokens TTL = 14 days (configurable).

## Resource overview

| Resource           | Endpoint                                | Method |
| ------------------ | --------------------------------------- | ------ |
| Health             | `/healthz`, `/readyz`, `/metrics`       | GET    |
| Auth               | `/auth/register`, `/auth/login`, `/auth/refresh` | POST  |
| Projects           | `/projects`, `/projects/{id}`           | CRUD   |
| Uploads            | `/uploads`, `/uploads/{id}`             | POST/GET |
| Standards          | `/standards`, `/standards/{code}`, `/standards/{code}/clauses` | GET |
| Compliance runs    | `/compliance/runs`, `/compliance/runs/{id}` | POST/GET |
| Compliance findings| `/compliance/runs/{id}/findings`        | GET    |
| Report             | `/compliance/runs/{id}/report`          | GET (redirect) |

## Errors

Every error response follows RFC 9457 (`application/problem+json`):

```json
{
  "type": "https://errors.tcvn-copilot.dev/not_found",
  "title": "Not Found",
  "status": 404,
  "detail": "project 4c0c... not found",
  "instance": "http://api/projects/4c0c...",
  "trace_id": "01HXXXXXXXXXXXXXXXXXXXXXXX"
}
```

`trace_id` matches the `x-request-id` response header, which the API echoes
on every request — include it when filing an issue.

## Quick walkthrough

```bash
# Register
curl -s -X POST $API/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"me@example.com","full_name":"Me","password":"a-strong-pw-123!"}'

# Login
TOK=$(curl -s -X POST $API/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"me@example.com","password":"a-strong-pw-123!"}' | jq -r .access_token)

# Create a project
PROJ=$(curl -s -X POST $API/projects \
  -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' \
  -d '{"name":"Hùng Vương Tower","building_type":"office"}' | jq -r .id)

# Upload a drawing
curl -s -X POST $API/uploads \
  -H "Authorization: Bearer $TOK" \
  -F project_id=$PROJ -F sheet_label=A-101 \
  -F file=@./A-101.pdf

# Start a compliance run
RUN=$(curl -s -X POST $API/compliance/runs \
  -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' \
  -d "{\"project_id\":\"$PROJ\",\"standards\":[\"QCVN_06_2022\",\"QCVN_10_2014\"]}" \
  | jq -r .id)

# Poll until done
while [ "$(curl -s -H "Authorization: Bearer $TOK" $API/compliance/runs/$RUN | jq -r .status)" != "succeeded" ]; do
  sleep 5; echo "still running…"
done

# Download the report (307 → presigned URL)
curl -L -H "Authorization: Bearer $TOK" $API/compliance/runs/$RUN/report -o report.pdf
```
