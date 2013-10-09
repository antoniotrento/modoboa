import factory
from . import models


class MailboxFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.Mailbox

    quota = 0
    use_domain_quota = True


class DomainFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.Domain

    quota = 10
    enabled = True