from rest_framework import serializers

from .models import ContactMessage

MESSAGE_MAX_LENGTH = 5000


class ContactMessageSerializer(serializers.ModelSerializer):
    """Maps the form's camelCase keys onto the model's snake_case fields.

    DRF's CharField trims whitespace by default, so a field holding only
    spaces arrives as an empty string rather than being saved as blanks.
    """

    firstName = serializers.CharField(
        source='first_name',
        max_length=100,
        required=False,
        allow_blank=True,
        default='',
    )
    lastName = serializers.CharField(
        source='last_name',
        max_length=100,
        required=False,
        allow_blank=True,
        default='',
    )
    email = serializers.EmailField(required=True, allow_blank=False)
    message = serializers.CharField(
        max_length=MESSAGE_MAX_LENGTH,
        required=False,
        allow_blank=True,
        default='',
    )

    class Meta:
        model = ContactMessage
        fields = ['firstName', 'lastName', 'email', 'message']

    def validate_email(self, value):
        # EmailField does not trim before validating, so " a@b.com " would be
        # rejected as malformed rather than accepted and cleaned.
        return value.strip()
