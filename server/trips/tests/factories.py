import factory
from django.utils import timezone
from faker import Factory

fake = Factory.create()
from trips import models


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.User

    username = factory.LazyAttribute(lambda x: fake.name())
    first_name = factory.LazyAttribute(lambda x: fake.name())
    last_name = factory.LazyAttribute(lambda x: fake.name())
    password = factory.PostGenerationMethodCall(lambda x: fake.password())
