from django.conf import settings
from django.db import models
from .profile import Profile


# The UserContext model captures contextual business flow information for agentive operations.
# This model supports dynamic business operations by storing relevant context data in a JSON field,
# which can be used to tailor AI-driven business processes.


class UserContext(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='user_contexts')
    business_flow = models.CharField(max_length=100, help_text='Name or type of the business flow')
    context_data = models.JSONField(blank=True, null=True, help_text='Detailed context information for agentive business flows')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Context for {self.profile.user.username} - {self.business_flow}"
