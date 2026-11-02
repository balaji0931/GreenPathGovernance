import re
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .qr_service import generate_qr_image_file

class Household(models.Model):
    """
    Household resident registration record (FR-16, FR-17, FR-18).
    Associated with exactly one Ward within a Village.
    Generates and persists a unique QR code for doorstep scanning.
    """
    uid = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        blank=True,
        help_text="Unique alphanumeric household identifier e.g. HH-VIL01-W01-0001"
    )
    village = models.ForeignKey(
        'governance.Village',
        on_delete=models.CASCADE,
        related_name='households'
    )
    ward = models.ForeignKey(
        'governance.Ward',
        on_delete=models.CASCADE,
        related_name='households'
    )
    head_name = models.CharField(
        max_length=150,
        verbose_name="Head of Household / Resident Name"
    )
    house_number = models.CharField(
        max_length=50,
        verbose_name="House / Door / Plot Number"
    )
    street_address = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Street / Locality Landmark"
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Contact Phone Number"
    )
    resident_user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='linked_household',
        help_text="Linked Household portal login account"
    )
    qr_code_image = models.ImageField(
        upload_to='qr_codes/',
        blank=True,
        null=True,
        help_text="Generated QR code PNG"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Active status. Inactive households are preserved in history (FR-22)."
    )
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['village', 'ward', 'house_number']
        verbose_name = 'Household'
        verbose_name_plural = 'Households'

    def __str__(self):
        return f"{self.head_name} (#{self.house_number}) [{self.uid}]"

    def clean(self):
        super().clean()
        # FR-21: The system shall prevent assigning a household to a ward outside the village
        v_id = getattr(self, 'village_id', None)
        w_id = getattr(self, 'ward_id', None)
        if v_id and w_id and self.ward:
            if self.ward.village_id != v_id:
                raise ValidationError({
                    'ward': f"Selected Ward '{self.ward.ward_number}' belongs to a different Gram Panchayat."
                })

    def save(self, *args, **kwargs):
        # Generate UID if empty
        if not self.uid:
            self.uid = self.generate_unique_uid()

        # Generate QR image if missing
        if not self.qr_code_image:
            qr_file = generate_qr_image_file(self)
            self.qr_code_image.save(qr_file.name, qr_file, save=False)

        # Enforce clean validation
        self.full_clean()

        super().save(*args, **kwargs)

    def generate_unique_uid(self):
        """
        Creates a structured, unique household UID:
        HH-[VILLAGE_CODE]-[WARD_NUMBER]-[SEQ]
        """
        v_part = re.sub(r'[^A-Z0-9]', '', self.village.code.upper())[:6]
        w_match = re.search(r'\d+', self.ward.ward_number)
        w_part = f"W{int(w_match.group()):02d}" if w_match else "W01"
        base_prefix = f"HH-{v_part}-{w_part}"

        count = Household.objects.filter(village=self.village, ward=self.ward).count() + 1
        candidate = f"{base_prefix}-{count:04d}"
        while Household.objects.filter(uid=candidate).exists():
            count += 1
            candidate = f"{base_prefix}-{count:04d}"
        return candidate
