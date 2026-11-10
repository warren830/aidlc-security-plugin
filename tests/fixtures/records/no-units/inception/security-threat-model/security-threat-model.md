# Security threat model

## Scope

- `inception/requirements-analysis/requirements.md`
- Review `scan-tm-77aa`

## Threats

- The upload endpoint accepts a file of any size, so one large request can fill the disk and stop the service for every user. Severity: SEVERE.
- A file name such as ../../app.env makes the upload handler write outside its own folder and replace the config. Severity: HIGH.
- The upload page sets no cache header. Severity: LOW.

## Mitigations for Construction

- Cap the upload size before reading the body.

## Record

```json
{
  "schema_version": 1,
  "scan": { "scan_id": "scan-tm-77aa", "scan_type": "THREAT_MODEL", "status": "COMPLETED" },
  "threats": [
    { "threat_id": "e1c5d3f0-7c1e", "statement": "The upload endpoint accepts a file of any size, so one large request can fill the disk and stop the service for every user.", "severity": "SEVERE", "status": "OPEN" },
    { "threat_id": "e1c5d3f0-4f8a", "statement": "A file name such as ../../app.env makes the upload handler write outside its own folder and replace the config.", "severity": "HIGH", "status": "OPEN" },
    { "threat_id": "e1c5d3f0-2b9a", "statement": "The upload page sets no cache header.", "severity": "LOW", "status": "OPEN" }
  ]
}
```
