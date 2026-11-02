from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Governance Profile'
    fk_name = 'user'

class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'get_village', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'profile__role', 'profile__village')

    def get_role(self, instance):
        return instance.profile.get_role_display() if hasattr(instance, 'profile') else '-'
    get_role.short_description = 'Role'

    def get_village(self, instance):
        return instance.profile.village.name if hasattr(instance, 'profile') and instance.profile.village else '-'
    get_village.short_description = 'Assigned Village'

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(UserProfile)
