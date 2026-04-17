from .models import LOCATION_CHOICES, SPECIES_CHOICES, COLOR_CHOICES, GENDER_CHOICES, CONDITION_CHOICES

def global_context(request):
    return {
        'location_choices': LOCATION_CHOICES,
        'species_choices': SPECIES_CHOICES,
        'color_choices': COLOR_CHOICES,
        'gender_choices': GENDER_CHOICES,
        'condition_choices': CONDITION_CHOICES,
    }
