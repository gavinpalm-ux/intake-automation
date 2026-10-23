# Extraction Accuracy (rules engine)

**Overall field accuracy: 96.2%**

| Field | Accuracy |
|---|---|
| contact_name | 100.0% |
| email | 100.0% |
| phone | 100.0% |
| property_type | 100.0% |
| unit_count | 93.3% |
| services | 93.3% |
| urgency | 86.7% |

## Misses

| Inquiry | Field | Expected | Got |
|---|---|---|---|
| INQ-003 | services | ['landscaping'] | ['landscaping', 'maintenance'] |
| INQ-003 | urgency | normal | low |
| INQ-004 | unit_count | 2 | None |
| INQ-007 | urgency | high | normal |
