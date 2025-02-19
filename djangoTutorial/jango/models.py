from django.db import models
from django.utils import timezone


# Create your models here.
class ChaiVariety(models.Model):
    CHAI_TYPE_CHOICES = [
        ('ML', 'Masala'),
        ('GR', 'Ginger'),
        ('KL', 'Kiwi'),
    ]
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='chai_images/')
    type = models.CharField(max_length=2, choices=CHAI_TYPE_CHOICES)
    date_added = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.name} - {self.get_type_display()} - Added on {self.date_added.strftime('%Y-%m-%d')}"
