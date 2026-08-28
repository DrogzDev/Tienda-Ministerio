from django.conf import settings
from django.db import models
from django.utils import timezone

from datetime import timedelta


class UserPresence(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="presence",
    )

    online = models.BooleanField(
        default=False,
    )

    last_seen = models.DateTimeField(
        default=timezone.now,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )


    class Meta:
        verbose_name = "Presencia de usuario"
        verbose_name_plural = "Presencias de usuarios"


    def __str__(self):
        return (
            f"{self.user.username} "
            f"- {'Online' if self.is_online else 'Offline'}"
        )


    @property
    def is_online(self):

        if not self.online:
            return False

        limit = (
            timezone.now()
            -
            timedelta(minutes=2)
        )

        return self.last_seen >= limit