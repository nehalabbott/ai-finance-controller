## 4. Failure Modes & Engineering Resolutions

| Failure Encountered | Root Cause | Engineering Resolution |
| :--- | :--- | :--- |
| **HTTP 404 / Deprecated Model** | Legacy endpoints sunset in environment updates. | Migrated to the modern `google-genai` SDK targeting current model endpoints. |
| **API Latency & Rate Limits** | Sequential row-by-row API querying caused long delays and rate-limit drops. | Re-architected ingestion to execute as a single batched JSON array request. |
| **Schema Inconsistency** | Unstructured text output complicates programmatic reconciliation. | Enforced native JSON schema validation (`response_mime_type="application/json"`). |