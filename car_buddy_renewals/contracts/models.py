from django.db import models

CLASSIFICATION_CHOICES = [
    ('unsure', 'Unsure'),
    ('approved', 'Approved'),
    ('refused', 'Refused'),
]

class EmailTranscript(models.Model):
    customer_email = models.EmailField()
    transcript = models.JSONField(default=list)  # Stores the full email conversation
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transcript for {self.customer_email} - {self.created_at}"


class PCPContract(models.Model):
    user = models.OneToOneField("User", on_delete=models.CASCADE, related_name="pcp_contract")
    car = models.CharField(max_length=255, blank=True, null=True)  # Make & Model
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - Expiry Date: {self.end_date}"


class User(models.Model):
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=50, blank=True, null=True)
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(unique=True)

    classification = models.CharField(
        max_length=10,
        choices=CLASSIFICATION_CHOICES,
        default='unsure'
    )
    is_contacted = models.BooleanField(default=False)  # True when an email is sent
    availability = models.TextField(blank=True, null=True)
    email_transcripts = models.ManyToManyField(EmailTranscript, blank=True, related_name='users')

    def __str__(self):
        return f"{self.email} - {self.classification}"
