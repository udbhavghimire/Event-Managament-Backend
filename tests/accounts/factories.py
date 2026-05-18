import factory
from factory.django import DjangoModelFactory
from faker import Faker

from accounts.models import User

fake = Faker()


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.LazyFunction(fake.unique.email)
    first_name = factory.LazyFunction(fake.first_name)
    last_name = factory.LazyFunction(fake.last_name)
    role = User.Role.ATTENDEE
    is_active = True
    password = factory.PostGenerationMethodCall("set_password", "testpassword123")
