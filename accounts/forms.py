# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class CustomUserCreationForm(UserCreationForm):
    # Your existing email field definition
    email = forms.EmailField(
        max_length=254,
        required=True,
        help_text='Required. Please enter a valid email address.'
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

    # --- ADD THIS NEW METHOD TO THE FORM ---
    def clean_email(self):
        """
        Validate that the email address is unique.
        """
        email = self.cleaned_data.get('email')
        if email:
            # Check if a user with this email already exists (case-insensitive)
            if User.objects.filter(email__iexact=email).exists():
                raise forms.ValidationError(
                    "This email address is already in use. Please use a different one."
                )
        return email