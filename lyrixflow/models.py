# core/models.py (or accounts/models.py)

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models
from django.conf import settings # To get AUTH_USER_MODEL
from django.utils import timezone

class ChatSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    artist_name = models.CharField(max_length=100)
    start_time = models.DateTimeField(auto_now_add=True)
    # Give the session a title, which we can generate from the first message
    title = models.CharField(max_length=100, default="New Chat")

    class Meta:
        ordering = ['-start_time'] # Show newest chats first

    def __str__(self):
        return f"'{self.title}' with {self.artist_name} for {self.user.username}"
    
class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    # Using a CharField for role allows for flexibility, e.g., 'user', 'model', 'system'
    role = models.CharField(max_length=10) # 'user' or 'model'
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp'] # Ensure messages are ordered correctly within a session

    def __str__(self):
        return f"{self.role} message in session {self.session.id} at {self.timestamp}"
    
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_pro = models.BooleanField(default=False)
    lyrics_generated_count = models.PositiveIntegerField(default=0)
    # You could add daily/monthly limits with DateFields if needed

    def __str__(self):
        return f"{self.user.username}'s Profile"

# Signal to create or update UserProfile whenever a User object is created/saved
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        # Ensure profile exists if user was created before profile model existed
        UserProfile.objects.get_or_create(user=instance)
    # instance.profile.save() # Not strictly necessary unless modifying profile here