import factory
from lily.google.gmail.models import GmailAccount, GmailMessage, GmailHeader, GmailLabel
from lily.users.factories import CustomUserFactory


class GmailAccountFactory(factory.DjangoModelFactory):
    user = factory.SubFactory(CustomUserFactory)

    class Meta:
        model = GmailAccount


class GmailMessageFactory(factory.DjangoModelFactory):
    account = factory.SubFactory(GmailAccountFactory)

    class Meta:
        model = GmailMessage


class GmailHeaderFactory(factory.DjangoModelFactory):
    message = factory.SubFactory(GmailMessageFactory)

    class Meta:
        model = GmailHeader


class GmailLabelFactory(factory.DjangoModelFactory):
    label_id = factory.Sequence(lambda n: 'Label_{0}'.format(n))

    class Meta:
        model = GmailLabel
