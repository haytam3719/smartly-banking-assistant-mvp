---
document_id: demo-transfer-policy
policy_type: transfer_policy
version: demo-1
effective_date: 2026-08-30
status: active
---

# DEMO — Transfer policy

**Synthetic fixture. Not an actual bank policy.**

## Rejected transfers

A rejected transfer can contain a machine-readable rejection reason.

### PAYMENT_LIMIT_EXCEEDED

For this demonstration, the code means that the operation exceeded an applicable transfer/payment threshold. The assistant should explain that the transfer was not executed and advise the customer to review the applicable limit or contact the bank through an authenticated channel if an adjustment is required.

### BENEFICIARY_RESTRICTED

For this demonstration, the beneficiary cannot currently receive the transfer. The customer should verify the beneficiary information or contact the bank through an authenticated channel.
