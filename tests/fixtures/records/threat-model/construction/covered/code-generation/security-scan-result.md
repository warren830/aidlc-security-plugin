# Security scan

```json
{ "schema_version": 2, "scan": { "scan_id": "scan-5e6f7a8b", "scan_type": "DIFF", "base_ref": "HEAD", "status": "COMPLETED", "region": "ap-southeast-1", "mcp_server": "awslabs.security-agent-mcp-server@0.2.1", "completed_at": "2026-11-02T09:40:00Z" }, "findings": [
  { "finding_id": "f-901", "name": "Expired token accepted", "risk_level": "HIGH", "status": "RESOLVED",
    "code_locations": [{ "file_path": "src/jwt.ts", "line_start": 30, "line_end": 34 }] }
], "threat_coverage": { "threat_model_scan_id": "scan-tm-1a2b3c4d", "threats": [
  { "threat_id": "T-001", "status": "MITIGATED", "evidence": [
    { "kind": "code", "file_path": "src/jwt.ts", "line_start": 12, "line_end": 20 },
    { "kind": "test", "file_path": "tests/jwt.test.ts", "name": "rejects a token signed with alg none" } ] },
  { "threat_id": "T-002", "status": "MITIGATED", "evidence": [
    { "kind": "finding", "finding_id": "f-901" },
    { "kind": "code", "file_path": "src/jwt.ts", "line_start": 30, "line_end": 34 } ] },
  { "threat_id": "T-003", "status": "NOT_APPLICABLE", "reason": "This unit builds auth-service only; api-gateway writes the access log." }
] } }
```
