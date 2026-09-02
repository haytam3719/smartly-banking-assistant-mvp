from enum import StrEnum


class RouteMode(StrEnum):
    RAG_ONLY = "RAG_ONLY"
    TOOLS_ONLY = "TOOLS_ONLY"
    HYBRID = "HYBRID"
    CLARIFY = "CLARIFY"
    UNSUPPORTED = "UNSUPPORTED"


class ToolName(StrEnum):
    GET_ACCOUNT_BALANCE = "get_account_balance"
    GET_TRANSACTIONS = "get_transactions"
    GET_CARD_INFO = "get_card_info"
    GET_TRANSFER_STATUS = "get_transfer_status"
    GET_CUSTOMER_INFO = "get_customer_info"


class EvidenceType(StrEnum):
    TOOL = "TOOL"
    RAG = "RAG"


class FailureKind(StrEnum):
    NOT_FOUND = "NOT_FOUND"
    FORBIDDEN = "FORBIDDEN"
    TIMEOUT = "TIMEOUT"
    UPSTREAM = "UPSTREAM"
    VALIDATION = "VALIDATION"
