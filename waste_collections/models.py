from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

class OutcomeChoices(models.TextChoices):
    COLLECTED = 'COLLECTED', 'Collected'
    MISSED = 'MISSED', 'Missed'

class MissedReasonChoices(models.TextChoices):
    LOCKED = 'LOCKED', 'House Locked'
    NOT_SEGREGATED = 'NOT_SEGREGATED', 'Waste Not Segregated'
    REFUSED = 'REFUSED', 'Resident Refused'
    NO_WASTE = 'NO_WASTE', 'No Waste'
    OTHER = 'OTHER', 'Other'

class CollectionRecord(models.Model):
    """
    Doorstep solid waste collection entry (FR-31 to FR-38).
    Records whether waste was collected or missed, segregation rating (1-5),
    waste categories (Wet, Dry, Sanitary), and collector identity.
    """
    household = models.ForeignKey(
        'households.Household',
        on_delete=models.CASCADE,
        related_name='collection_records'
    )
    collector = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_collections'
    )
    village = models.ForeignKey(
        'governance.Village',
        on_delete=models.CASCADE,
        related_name='collection_records'
    )
    ward = models.ForeignKey(
        'governance.Ward',
        on_delete=models.CASCADE,
        related_name='collection_records'
    )
    collection_date = models.DateField(
        default=timezone.localdate,
        db_index=True,
        help_text="Server-assigned collection date (Asia/Kolkata)"
    )
    collection_time = models.TimeField(
        default=timezone.localtime,
        help_text="Server-assigned collection time"
    )
    outcome = models.CharField(
        max_length=20,
        choices=OutcomeChoices.choices,
        default=OutcomeChoices.COLLECTED
    )
    is_segregated = models.BooleanField(
        null=True,
        blank=True,
        help_text="True if segregated, False if unsegregated"
    )
    waste_wet = models.BooleanField(
        default=False,
        verbose_name="Wet / Organic Waste"
    )
    waste_dry = models.BooleanField(
        default=False,
        verbose_name="Dry / Recyclable Waste"
    )
    waste_sanitary = models.BooleanField(
        default=False,
        verbose_name="Sanitary / Hazardous Waste"
    )
    segregation_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="1 to 5 Star Rating (Required if outcome is COLLECTED)"
    )
    missed_reason = models.CharField(
        max_length=30,
        choices=MissedReasonChoices.choices,
        blank=True,
        help_text="Configured reason for missed visit (Required if outcome is MISSED)"
    )
    remarks = models.TextField(
        blank=True,
        help_text="Optional collector field remarks"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-collection_date', '-collection_time']
        verbose_name = 'Collection Record'
        verbose_name_plural = 'Collection Records'

    def __str__(self):
        return f"{self.household.uid} | {self.outcome} on {self.collection_date}"

    def clean(self):
        super().clean()

        # Enforce outcome-specific validation rules
        if self.outcome == OutcomeChoices.COLLECTED:
            if self.segregation_rating is None or not (1 <= self.segregation_rating <= 5):
                raise ValidationError({
                    'segregation_rating': 'A valid segregation rating from 1 to 5 is required for a collected outcome.'
                })
            if self.is_segregated is None:
                raise ValidationError({
                    'is_segregated': 'Segregation status (Yes/No) is required for a collected outcome.'
                })
            self.missed_reason = ''
        elif self.outcome == OutcomeChoices.MISSED:
            if not self.missed_reason:
                raise ValidationError({
                    'missed_reason': 'A missed reason is mandatory when outcome is Missed.'
                })
            self.segregation_rating = None
            self.is_segregated = None
            self.waste_wet = False
            self.waste_dry = False
            self.waste_sanitary = False

        # Multi-tenancy check: Household must belong to record's village
        if self.household_id and self.village_id:
            if self.household.village_id != self.village_id:
                raise ValidationError({
                    'household': 'Household belongs to a different Gram Panchayat than this record.'
                })

    def save(self, *args, **kwargs):
        # Auto-link village and ward from household if omitted
        if self.household_id:
            if not self.village_id:
                self.village = self.household.village
            if not self.ward_id:
                self.ward = self.household.ward

        self.full_clean()
        super().save(*args, **kwargs)
