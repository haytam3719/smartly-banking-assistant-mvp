from app.infrastructure.persistence.audit import SafeAuditRepository


def test_audit_sanitizer_removes_sensitive_payload_keys() -> None:
    raw = {
        "tool": "get_account_balance",
        "data": {"available_balance": 1200},
        "balance": 1200,
        "nested": {"transactions": [{"amount": 5}], "status": "ok"},
    }
    safe = SafeAuditRepository._sanitize(raw)
    assert "data" not in safe
    assert "balance" not in safe
    assert safe["nested"] == {"status": "ok"}
