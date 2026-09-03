# API examples

## Balance — tool only

```bash
curl -s http://localhost:8000/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":"C1024","message":"Quel est mon solde ?"}'
```

## International fees — RAG only

```bash
curl -s http://localhost:8000/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":"C1024","message":"Quels sont les frais d un virement international ?"}'
```

## Rejected transfer — hybrid

```bash
curl -s http://localhost:8000/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":"C1024","message":"Mon virement TR4587 a été refusé. Pourquoi et que dois-je faire ?"}'
```
