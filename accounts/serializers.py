from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import Attendee, Organizer, User


class UserSerializer(serializers.ModelSerializer):
    """Read-only representation returned after register / login / me."""

    organisation_name = serializers.SerializerMethodField()
    contact_phone = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "role",
            "organisation_name",
            "contact_phone",
            "created_at",
        ]
        read_only_fields = fields

    def get_organisation_name(self, obj: User) -> str | None:
        if obj.role != User.Role.ORGANIZER:
            return None
        try:
            return obj.organizer.organisation_name
        except Organizer.DoesNotExist:
            return None

    def get_contact_phone(self, obj: User) -> str | None:
        if obj.role != User.Role.ORGANIZER:
            return None
        try:
            return obj.organizer.contact_phone
        except Organizer.DoesNotExist:
            return None


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    full_name = serializers.CharField(max_length=255)
    role = serializers.ChoiceField(choices=["ORGANIZER", "ATTENDEE"])
    # Required only when role == ORGANIZER
    organisation_name = serializers.CharField(max_length=255, required=False, allow_blank=False)
    contact_phone = serializers.CharField(max_length=50, required=False, allow_blank=True)

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate(self, attrs: dict) -> dict:
        if attrs["role"] == "ORGANIZER" and not attrs.get("organisation_name"):
            raise serializers.ValidationError(
                {"organisation_name": "This field is required for organizers."}
            )
        return attrs

    def create(self, validated_data: dict) -> User:
        organisation_name = validated_data.pop("organisation_name", None)
        contact_phone = validated_data.pop("contact_phone", None) or None
        role = validated_data["role"]

        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            full_name=validated_data["full_name"],
            role=role,
        )

        if role == "ORGANIZER":
            Organizer.objects.create(
                user=user,
                organisation_name=organisation_name,
                contact_phone=contact_phone,
            )
        else:
            Attendee.objects.create(user=user)

        return user


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "full_name", "role", "is_active", "created_at"]
        read_only_fields = fields


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs: dict) -> dict:
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["email"],
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("This account has been deactivated.")
        attrs["user"] = user
        return attrs
