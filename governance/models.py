from django.db import models

class Village(models.Model):
    """
    Gram Panchayat / Village administrative entity.
    Scopes Village Managers, Waste Collectors, Wards, and Households.
    """
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique alphanumeric village code e.g. VIL-SHIVAJI-01"
    )
    name = models.CharField(max_length=150)
    district = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, default='Maharashtra')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Village / Gram Panchayat'
        verbose_name_plural = 'Villages / Gram Panchayats'

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def total_wards_count(self):
        return self.wards.count()

    @property
    def assigned_managers(self):
        return self.user_profiles.filter(role='VILLAGE_MANAGER')

    @property
    def primary_manager(self):
        return self.assigned_managers.first()


class Ward(models.Model):
    """
    Ward subdivision within a Village.
    Every Household belongs to exactly one Ward.
    """
    village = models.ForeignKey(
        Village,
        on_delete=models.CASCADE,
        related_name='wards'
    )
    ward_number = models.CharField(max_length=20, help_text="e.g. Ward 01")
    ward_name = models.CharField(max_length=100, blank=True, help_text="e.g. North Bazaar")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['village', 'ward_number']
        unique_together = ('village', 'ward_number')
        verbose_name = 'Ward'
        verbose_name_plural = 'Wards'

    def __str__(self):
        name_str = f" - {self.ward_name}" if self.ward_name else ""
        return f"{self.village.name} | {self.ward_number}{name_str}"
