from __future__ import annotations

GROUPS = {
    'user': 'base.group_user',
    'admin': 'base.group_system',
}

_METHODS: dict = {}


def api_method(name, group='user'):
    """Register a plain function as a callable method of the standalone app's API."""

    def decorator(func):
        _METHODS[name] = (func, GROUPS[group])
        return func

    return decorator


def get_method(name):
    """Return the ``(func, group)`` pair registered under ``name``, or ``None``."""
    return _METHODS.get(name)
