class ApplicationError(Exception):
    """Base error safe to map to an API response."""


class InvalidRoutingPlan(ApplicationError):
    pass


class BankingToolError(ApplicationError):
    pass


class RetrievalError(ApplicationError):
    pass
