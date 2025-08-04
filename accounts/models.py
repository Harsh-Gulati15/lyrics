# accounts/models.py
from django.db import models
from django.conf import settings # To get AUTH_USER_MODEL
from django.utils import timezone
import secrets # For generating secure tokens
import hashlib # For hashing tokens

class RememberMeToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    selector = models.CharField(max_length=12, unique=True)
    hashed_validator = models.CharField(max_length=64) # SHA256 hash
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"Token for {self.user.username} expiring at {self.expires_at}"

    @staticmethod
    def generate_token():
        """Generates a public selector and a secret validator."""
        selector = secrets.token_hex(6)
        validator = secrets.token_hex(20) # Secret part
        return selector, validator

    def set_validator(self, validator):
        """Hashes and stores the validator."""
        self.hashed_validator = hashlib.sha256(validator.encode()).hexdigest()

    def check_validator(self, validator):
        """Checks if the provided validator matches the stored hash."""
        return self.hashed_validator == hashlib.sha256(validator.encode()).hexdigest()

    def is_expired(self):
        return timezone.now() > self.expires_at