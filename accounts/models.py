from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class RoleChoices(models.TextChoices):
    SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'
    VILLAGE_MANAGER = 'VILLAGE_MANAGER', 'Village Manager'
    WASTE_COLLECTOR = 'WASTE_COLLECTOR', 'Waste Collector'
    HOUSEHOLD = 'HOUSEHOLD', 'Household'

class UserProfile(models.Model):
    """
    Extends Django's User model with role-based governance metadata
    and Gram Panchayat (village) assignment scoping.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    role = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,
        default=RoleChoices.HOUSEHOLD
    )
    village = models.ForeignKey(
        'governance.Village',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_profiles',
        help_text="Assigned Village for Village Managers and Waste Collectors"
    )
    phone_number = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__username']
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        village_label = f" [{self.village.code}]" if self.village else ""
        return f"{self.user.username} ({self.get_role_display()}){village_label}"

    @property
    def is_super_admin(self):
        return self.role == RoleChoices.SUPER_ADMIN or self.user.is_superuser

    @property
    def is_village_manager(self):
        return self.role == RoleChoices.VILLAGE_MANAGER

    @property
    def is_waste_collector(self):
        return self.role == RoleChoices.WASTE_COLLECTOR

    @property
    def is_household(self):
        return self.role == RoleChoices.HOUSEHOLD


@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, created, **kwargs):
    """
    Automatically provisions a UserProfile for newly created users.
    Superusers automatically receive SUPER_ADMIN role.
    """
    if created:
        role = RoleChoices.SUPER_ADMIN if instance.is_superuser else RoleChoices.HOUSEHOLD
        UserProfile.objects.get_or_create(user=instance, defaults={'role': role})
    else:
        # If user is upgraded to superuser, keep role synchronized if desired
        if hasattr(instance, 'profile') and instance.is_superuser and instance.profile.role != RoleChoices.SUPER_ADMIN:
            instance.profile.role = RoleChoices.SUPER_ADMIN
            instance.profile.save()
