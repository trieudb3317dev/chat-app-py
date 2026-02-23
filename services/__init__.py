import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # add project root
"""Service layer: business logic separated from routers/controllers.

This package re-exports commonly-used service functions so you can import
them directly from `services` for convenience, e.g.:

	from services import create_user

Or import the module:

	from services import db_service

Both styles are supported.
"""

from services.user_service import (
	create_user,
	# create_post,
	# create_item,
	# attach_item_to_user,
	# get_user_with_relations,
)

# also keep the module available
from . import user_service
from .mailer_service import (
	send_email,
	send_activation_email,
	send_reset_password_email,
	send_simple_notification,
)

__all__ = [
	"create_user",
	# "create_post",
	# "create_item",
	# "attach_item_to_user",
	# "get_user_with_relations",
	"user_service",
	"send_email",
	"send_activation_email",
	"send_reset_password_email",
	"send_simple_notification",
]
