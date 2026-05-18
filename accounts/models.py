from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email: str, password: str | None = None, **extra_fields):
        if not email:
            raise ValueError("Email address is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ORGANIZER = "ORGANIZER", "Organizer"
        ATTENDEE = "ATTENDEE", "Attendee"
        ADMIN = "ADMIN", "Admin"

    # Remove the built-in username field
    username = None

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=Role.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name", "role"]

    objects = UserManager()

    class Meta:
        db_table = "accounts_user"

    def __str__(self) -> str:
        return self.email


class Organizer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    organisation_name = models.CharField(max_length=255)
    contact_phone = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        db_table = "accounts_organizer"

    def __str__(self) -> str:
        return self.organisation_name


class Attendee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    preferences = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "accounts_attendee"

    def __str__(self) -> str:
        return self.user.email
