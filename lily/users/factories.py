from random import randint, choice
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from factory.declarations import LazyAttribute
from factory.django import DjangoModelFactory
from factory.helpers import post_generation
from faker.factory import Factory

from lily.users.models import LilyUser


faker = Factory.create()


class LilyUserFactory(DjangoModelFactory):
    password = make_password('lilyuser')

    first_name = LazyAttribute(lambda o: faker.first_name())
    preposition = LazyAttribute(lambda o: choice(['van der', 'vd', 'van', 'de', 'ten', 'von', 'van de', 'van den']) if bool(randint(0, 1)) else '')
    last_name = LazyAttribute(lambda o: faker.last_name())
    email = LazyAttribute(lambda o: faker.email())
    is_active = LazyAttribute(lambda o: bool(randint(0, 1)))

    phone_number = LazyAttribute(lambda o: faker.phone_number())

    language = LazyAttribute(lambda o: faker.language_code())
    timezone = LazyAttribute(lambda o: faker.timezone())

    class Meta:
        model = LilyUser


class LilySuperUserFactory(LilyUserFactory):
    password = make_password('lilysuperuser')

    is_superuser = True
    is_staff = True

    @post_generation
    def groups(self, create, extracted, **kwargs):
        group = Group.objects.get_or_create(name='account_admin')[0]
        self.groups.add(group)
