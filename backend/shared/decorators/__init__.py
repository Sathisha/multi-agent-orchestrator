"""Permission decorators package."""

from shared.decorators.permissions import require_permission, require_super_admin

__all__ = ['require_permission', 'require_super_admin']
