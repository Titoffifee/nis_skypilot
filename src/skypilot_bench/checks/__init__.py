"""Reproducible local checks."""


def require(condition, message):
    if not condition:
        raise AssertionError(message)
