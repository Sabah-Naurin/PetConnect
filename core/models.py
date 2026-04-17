from django.db import models
from django.contrib.auth.models import AbstractUser

SPECIES_CHOICES = [('Dog', 'Dog'), ('Cat', 'Cat'), ('Bird', 'Bird'), ('Rabbit', 'Rabbit'), ('Reptile', 'Reptile'), ('Other', 'Other')]
COLOR_CHOICES = [('Black', 'Black'), ('White', 'White'), ('Brown', 'Brown'), ('Gray', 'Gray'), ('Golden', 'Golden'), ('Ginger', 'Ginger'), ('Calico', 'Calico'), ('Mixed', 'Mixed')]
GENDER_CHOICES = [('Male', 'Male'), ('Female', 'Female'), ('Unknown', 'Unknown')]
CONDITION_CHOICES = [('Healthy', 'Healthy'), ('Injured', 'Injured'), ('Deceased', 'Deceased')]
APPROVAL_CHOICES = [('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')]
EVENT_TYPE_CHOICES = [('Reported', 'Reported'), ('Sighting', 'Sighting'), ('Update', 'Update'), ('Rescue', 'Rescue'), ('Fundraiser', 'Fundraiser'), ('Reunited', 'Reunited')]
LOCATION_CHOICES = [('Dhanmondi', 'Dhanmondi'), ('Gulshan 1', 'Gulshan 1'), ('Gulshan 2', 'Gulshan 2'), ('Banani', 'Banani'), ('Uttara', 'Uttara'), ('Mirpur 1', 'Mirpur 1'), ('Mirpur 10', 'Mirpur 10'), ('Mirpur 12', 'Mirpur 12'), ('Mohammadpur', 'Mohammadpur'), ('Bashundhara R/A', 'Bashundhara R/A'), ('Farmgate', 'Farmgate'), ('Tejgaon', 'Tejgaon'), ('Malibagh', 'Malibagh'), ('Banasree', 'Banasree'), ('Lalmatia', 'Lalmatia'), ('Baridhara', 'Baridhara'), ('Nikunja', 'Nikunja'), ('Khilgaon', 'Khilgaon'), ('Badda', 'Badda'), ('Puran Dhaka', 'Puran Dhaka')]

class Profile(AbstractUser):
    location = models.CharField(max_length=255, choices=LOCATION_CHOICES, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.username

class BasePetReport(models.Model):
    author = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='reports')
    image = models.ImageField(upload_to='pet_images/')
    species = models.CharField(max_length=50, choices=SPECIES_CHOICES)
    primary_color = models.CharField(max_length=50, choices=COLOR_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    location = models.CharField(max_length=255, choices=LOCATION_CHOICES)
    is_resolved = models.BooleanField(default=False)
    note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Report {self.id} by {self.author.username}"

class LostReport(models.Model):
    base_report = models.OneToOneField(BasePetReport, on_delete=models.CASCADE, related_name='lost_report')
    breed = models.CharField(max_length=100, blank=True)
    pet_name = models.CharField(max_length=100, blank=True)
    age = models.CharField(max_length=50, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)
    special_marks = models.TextField(blank=True)
    date_lost = models.DateField()
    time_lost = models.TimeField()

    def __str__(self):
        return f"Lost Report: {self.pet_name}"

class SightingReport(models.Model):
    base_report = models.OneToOneField(BasePetReport, on_delete=models.CASCADE, related_name='sighting_report')
    parent_report = models.ForeignKey(LostReport, on_delete=models.SET_NULL, null=True, blank=True, related_name='cross_matches')
    condition = models.CharField(max_length=100, choices=CONDITION_CHOICES) 
    in_custody = models.BooleanField(default=False)
    current_custodian = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='custody_reports')
    date_sighted = models.DateField()
    time_sighted = models.TimeField(null=True, blank=True)

    def __str__(self):
        return f"Sighting Report {self.id}"

class RescueVerification(models.Model):
    sighting = models.ForeignKey(SightingReport, on_delete=models.CASCADE, related_name='rescue_verifications')
    rescuer = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='rescues')
    proof_image = models.ImageField(upload_to='rescue_proofs/')
    status = models.CharField(max_length=50, choices=APPROVAL_CHOICES, default='Pending') # Pending, Approved, Rejected
    verified_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_rescues')

class OwnershipClaim(models.Model):
    sighting_report = models.ForeignKey(SightingReport, on_delete=models.CASCADE, related_name='claims')
    lost_report = models.ForeignKey(LostReport, on_delete=models.CASCADE)
    owner = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='claims')
    CLAIM_TYPE_CHOICES = [('Manual', 'Manual'), ('ML Match', 'ML Match')]
    claim_type = models.CharField(max_length=50, choices=CLAIM_TYPE_CHOICES, default='Manual')
    approval_status = models.CharField(max_length=50, choices=APPROVAL_CHOICES, default='Pending')

class MedicalFundRequest(models.Model):
    sighting_report = models.OneToOneField(SightingReport, on_delete=models.CASCADE, related_name='fund_request')
    prescription_image = models.ImageField(upload_to='prescriptions/')
    target_amount = models.DecimalField(max_digits=10, decimal_places=2)
    current_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    approval_status = models.CharField(max_length=50, choices=APPROVAL_CHOICES, default='Pending')
    rescuers_note = models.TextField()
    current_condition = models.CharField(max_length=200)

class DonationLog(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    )

    medical_fund_request = models.ForeignKey(MedicalFundRequest, on_delete=models.CASCADE, related_name='donations')
    donor = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    trx_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    timestamp = models.DateTimeField(auto_now_add=True)

class AdoptionPost(models.Model):
    base_report = models.OneToOneField(BasePetReport, on_delete=models.CASCADE, related_name='adoption_post', null=True, blank=True)
    owner = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='adoption_posts')
    name = models.CharField(max_length=100)
    age = models.CharField(max_length=50)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES)
    breed = models.CharField(max_length=100)
    vaccination_status = models.CharField(max_length=100)
    sterilization_status = models.CharField(max_length=100)
    food_habit = models.TextField()
    requirements = models.TextField()
    adoption_status = models.CharField(max_length=50, default='Available')

class ReportTimeline(models.Model):
    pet = models.ForeignKey(BasePetReport, on_delete=models.CASCADE, related_name='timeline')
    actor = models.ForeignKey(Profile, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=100, choices=EVENT_TYPE_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('CLAIM_APPROVED', 'Ownership Verified'),
        ('NEW_SIGHTING', 'New Sighting Alert'),
        ('FUND_ACTIVE', 'Medical Fund Approved'),
        ('RESCUE_CONFIRMED', 'Rescue Verified'),
        ('RESCUE_REJECTED', 'Rescue Proof Rejected'),
        ('DONATION_REVIEW', 'Review Donation'),
        ('DONATION_SUCCESS', 'Donation Received'),
        ('CLAIM_REJECTED', 'Ownership Claim Rejected'),
    )

    recipient = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='notifications')
    notif_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    related_id = models.IntegerField(null=True, blank=True)
    message = models.CharField(max_length=255)
    link = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
