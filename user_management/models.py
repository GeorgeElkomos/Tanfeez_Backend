from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
# Removed encrypted fields import - using standard Django fields now
from account_and_entitys.models import XX_Entity
class xx_UserManager(BaseUserManager):
    def create_user(self, username, password=None, role='user', user_level=None):
        if not username:
            raise ValueError('Username is required')

        user = self.model(username=username, role=role)
        user.set_password(password)

        # Assign user level if provided, otherwise use the default
        if user_level:
            user.user_level = user_level
        else:
            # Get the default user level (the one with the lowest level_order)
            try:
                default_level = xx_UserLevel.objects.order_by('level_order').first()
                if default_level:
                    user.user_level = default_level
                else:
                    # No user levels exist yet, log a warning
                    print("Warning: No user levels found in the system. User created without a level.")
            except Exception as e:
                print(f"Error assigning default user level: {e}")

        user.save(using=self._db)
        return user

    def create_superuser(self, username, password):
        # For superusers, try to get the highest level
        try:
            highest_level = xx_UserLevel.objects.order_by('-level_order').first()
        except:
            highest_level = None

        user = self.create_user(username, password, role='admin', user_level=highest_level)
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user


class xx_UserLevel(models.Model):
    """Model to represent user levels/roles in the system."""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(null=True, blank=True)  # Changed from EncryptedTextField
    level_order = models.PositiveIntegerField(default=1, help_text="Order of the level for hierarchy")

    class Meta:
        db_table = 'XX_USER_LEVEL_XX'
        ordering = ['level_order']

    def __str__(self):
        return self.name




class xx_User(AbstractBaseUser, PermissionsMixin):
    """Custom user model with roles for admin and regular users"""
    ROLE_CHOICES = (('admin', 'Admin'), ('user', 'User'), ('superadmin', 'SuperAdmin'))
    username = models.CharField(max_length=255, unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=True)
    can_transfer_budget = models.BooleanField(default=True)  # Permission specific to this app
    user_level = models.ForeignKey(
        xx_UserLevel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )

    USERNAME_FIELD = 'username'

    objects = xx_UserManager()

    def __str__(self):
        return self.username

    class Meta:
        # Use the exact name of the existing table in your Oracle database
        db_table = 'XX_USER_XX'
        # If you have other Meta options, keep them here


class xx_UserAbility(models.Model):
    """Model to represent user abilities or permissions."""
    user = models.ForeignKey(xx_User, on_delete=models.CASCADE, related_name='abilities')
    Entity = models.ForeignKey(XX_Entity, on_delete=models.CASCADE, related_name='user_abilities', null=True, blank=True)
    Type = models.CharField(max_length=50, null=True, blank=True, choices=[
        ('edit', 'edit'),
        ('approve', 'approve'),
    ])
    class Meta:
        db_table = 'XX_USER_ABILITY_XX'
        unique_together = ('user', 'Entity', 'Type')






class xx_notification(models.Model):
    """Model to represent notifications for users."""
    user = models.ForeignKey(xx_User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()  # Changed from EncryptedTextField
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_system_read = models.BooleanField(default=False)  # For tracking if the notification was read on the OS system
    is_shown = models.BooleanField(default=True)  # For tracking if the notification was shown to the user

    class Meta:
        db_table = 'XX_NOTIFICATION_XX'
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:20]}"