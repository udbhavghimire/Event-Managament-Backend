import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user_factory):
    user = user_factory()
    api_client.force_authenticate(user=user)
    return api_client, user


@pytest.fixture
def organizer_client(api_client, user_factory):
    organizer = user_factory(role="organizer")
    api_client.force_authenticate(user=organizer)
    return api_client, organizer
