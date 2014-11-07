import datetime

from factory.declarations import SubFactory, LazyAttribute, SelfAttribute
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyDecimal, FuzzyDate, FuzzyChoice
from faker.factory import Factory

from lily.accounts.factories import AccountFactory
from lily.deals.models import Deal
from lily.tenant.factories import TenantFactory
from lily.users.factories import CustomUserFactory


faker = Factory.create()


class DealFactory(DjangoModelFactory):
    tenant = SubFactory(TenantFactory)
    name = LazyAttribute(lambda o: faker.word())
    account = SubFactory(AccountFactory, tenant=SelfAttribute('..tenant'))
    amount = FuzzyDecimal(42.7)
    expected_closing_date = FuzzyDate(datetime.date(2015, 1, 1), datetime.date(2016, 1, 1))
    assigned_to = SubFactory(CustomUserFactory, tenant=SelfAttribute('..tenant'))
    stage = FuzzyChoice(dict(Deal.STAGE_CHOICES).keys())

    class Meta:
        model = Deal
