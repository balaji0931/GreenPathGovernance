from django import forms
from .models import CollectionRecord, OutcomeChoices, MissedReasonChoices
from households.models import Household

class DoorstepCollectionForm(forms.ModelForm):
    """
    Field form submitted by Waste Collector at doorstep (FR-31 to FR-37).
    """
    household_uid = forms.CharField(
        widget=forms.HiddenInput()
    )
    is_segregated = forms.ChoiceField(
        choices=[('true', 'Yes, Segregated'), ('false', 'No, Mixed')],
        required=False,
        widget=forms.RadioSelect(attrs={'class': 'text-emerald-600 focus:ring-emerald-500'})
    )

    class Meta:
        model = CollectionRecord
        fields = [
            'outcome',
            'is_segregated',
            'waste_wet',
            'waste_dry',
            'waste_sanitary',
            'segregation_rating',
            'missed_reason',
            'remarks',
        ]
        widgets = {
            'outcome': forms.RadioSelect(attrs={'class': 'text-emerald-600 focus:ring-emerald-500'}),
            'waste_wet': forms.CheckboxInput(attrs={'class': 'w-5 h-5 text-emerald-600 rounded border-slate-300 focus:ring-emerald-500'}),
            'waste_dry': forms.CheckboxInput(attrs={'class': 'w-5 h-5 text-blue-600 rounded border-slate-300 focus:ring-blue-500'}),
            'waste_sanitary': forms.CheckboxInput(attrs={'class': 'w-5 h-5 text-rose-600 rounded border-slate-300 focus:ring-rose-500'}),
            'segregation_rating': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm font-semibold',
            }),
            'missed_reason': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-amber-500 focus:border-amber-500 text-sm',
            }),
            'remarks': forms.Textarea(attrs={
                'rows': 2,
                'class': 'w-full px-4 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 text-xs',
                'placeholder': 'Optional doorstep observations...',
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        outcome = cleaned_data.get('outcome')
        is_seg_str = cleaned_data.get('is_segregated')

        if outcome == OutcomeChoices.COLLECTED:
            if not is_seg_str:
                self.add_error('is_segregated', "Please select whether the waste was segregated or mixed.")
            else:
                cleaned_data['is_segregated'] = (is_seg_str == 'true')

            rating = cleaned_data.get('segregation_rating')
            if not rating:
                self.add_error('segregation_rating', "Segregation rating (1 to 5) is required for a collected outcome (FR-34).")

            # Reset missed reason if collected
            cleaned_data['missed_reason'] = ''

        elif outcome == OutcomeChoices.MISSED:
            reason = cleaned_data.get('missed_reason')
            if not reason:
                self.add_error('missed_reason', "Please select a reason why collection was missed (FR-36).")

            cleaned_data['is_segregated'] = None
            cleaned_data['segregation_rating'] = None
            cleaned_data['waste_wet'] = False
            cleaned_data['waste_dry'] = False
            cleaned_data['waste_sanitary'] = False

        return cleaned_data

