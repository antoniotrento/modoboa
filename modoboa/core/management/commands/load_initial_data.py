"""A management command to load Modoboa initial data:

* Create a default super admin if none exists
* Create groups and permissions

"""

from __future__ import unicode_literals

from functools import reduce

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from modoboa.lib.cryptutils import random_key
from modoboa.lib.permissions import add_permissions_to_group

from ... import constants
from ... import extensions
from ... import models
from ... import signals


class Command(BaseCommand):
    """Command definition."""

    help = "Load Modoboa initial data"

    def add_arguments(self, parser):
        """Add extra arguments to command."""
        parser.add_argument(
            "--admin-username", default="admin",
            help="Username of the initial super administrator."
        )
        parser.add_argument(
            "--extra-fixtures", action="store_true", default=False,
            help="Also load some fixtures from the admin application."
        )

    def handle(self, *args, **options):
        """Command entry point."""
        extensions.exts_pool.load_all()

        if not models.User.objects.filter(is_superuser=True).count():
            admin = models.User(
                username=options["admin_username"], is_superuser=True)
            admin.set_password("password")
            admin.save()
            models.ObjectAccess.objects.create(
                user=admin, content_object=admin, is_owner=True)

        lc = models.LocalConfig.objects.first()
        condition = (
            "core" not in lc._parameters or
            "secret_key" not in lc._parameters["core"])
        if condition:
            lc.parameters.set_value("secret_key", random_key())
            lc.save()

        groups = list(constants.PERMISSIONS.keys())
        for groupname in groups:
            group, created = Group.objects.get_or_create(name=groupname)
            results = signals.extra_role_permissions.send(
                sender=self.__class__, role=groupname)
            permissions = constants.PERMISSIONS.get(groupname, [])
            if results:
                permissions += reduce(
                    lambda a, b: a + b, [result[1] for result in results])
            if not permissions:
                continue
            add_permissions_to_group(group, permissions)

        for extname in list(extensions.exts_pool.extensions.keys()):
            extension = extensions.exts_pool.get_extension(extname)
            extension.load_initial_data()
            signals.initial_data_loaded.send(
                sender=self.__class__, extname=extname)

        if options["extra_fixtures"]:
            from modoboa.admin import factories
            factories.populate_database()
