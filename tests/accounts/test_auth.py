import pytest
from django.urls import reverse
from rest_framework import status

from tests.accounts.factories import UserFactory  # noqa: F401 — used via fixtures

pytestmark = pytest.mark.django_db


class TestRegister:
    def test_register_success(self, api_client):
        url = reverse("accounts:register")
        payload = {
            "email": "newuser@example.com",
            "first_name": "Jane",
            "last_name": "Doe",
            "role": "attendee",
            "password": "StrongPass1!",
            "password_confirm": "StrongPass1!",
        }
        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_register_password_mismatch(self, api_client):
        url = reverse("accounts:register")
        payload = {
            "email": "x@example.com",
            "first_name": "A",
            "last_name": "B",
            "role": "attendee",
            "password": "pass1",
            "password_confirm": "pass2",
        }
        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_duplicate_email(self, api_client):
        user = UserFactory(email="dup@example.com")
        url = reverse("accounts:register")
        payload = {
            "email": user.email,
            "first_name": "X",
            "last_name": "Y",
            "role": "attendee",
            "password": "StrongPass1!",
            "password_confirm": "StrongPass1!",
        }
        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestMe:
    def test_me_requires_auth(self, api_client):
        url = reverse("accounts:me")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_returns_current_user(self, api_client):
        user = UserFactory()
        api_client.force_authenticate(user=user)
        url = reverse("accounts:me")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == user.email
