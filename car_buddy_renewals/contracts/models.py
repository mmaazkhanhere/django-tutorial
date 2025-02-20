from django.db import models

class PCPContract(models.Model):
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=50, blank=True, null=True)
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
    email_address = models.EmailField(unique=True)
    car_details = models.CharField(max_length=255, blank=True, null=True)  # Make & Model
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"{self.first_name} {self.last_name} - Expiry Date: {self.end_date}"


class EmailTranscript(models.Model):
    customer_email = models.EmailField()
    transcript = models.JSONField(default=list)  # Stores the full email conversation
    created_at = models.DateTimeField(auto_now_add=True)



class User(models.Model):
    CLASSIFICATION_CHOICES = [
        ('unsure', 'Unsure'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
    ]

    email = models.EmailField(unique=True)
    classification = models.CharField(
        max_length=10,
        choices=CLASSIFICATION_CHOICES,
        default='unsure'
    )
    is_contacted = models.BooleanField(default=False)  # True when an email is sent
    pcp_contract = models.ForeignKey(PCPContract, on_delete=models.CASCADE, related_name='users')
    email_transcript = models.ForeignKey(EmailTranscript, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')

    def __str__(self):
        return f"{self.email} - {self.classification}"
