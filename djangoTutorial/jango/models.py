from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


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

# One to Many Model

class ChaiReviews(models.Model):
    chai = models.ForeignKey(ChaiVariety, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField()
    comment = models.TextField() 
    date_added = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} - {self.chai.name} - {self.rating} stars"
    

# Many to Many Model

class Store(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    chai_varieties = models.ManyToManyField(ChaiVariety, related_name='stores')

    def __str__(self):
        return self.name
    

# One to One Model

class ChaiCertificate(models.Model):
    chai = models.OneToOneField(ChaiVariety, on_delete=models.CASCADE, related_name='certificate')
    certificate_number = models.CharField(max_length=20, unique=True)
    issue_date = models.DateField(default=timezone.now)
    valid_until = models.DateField()

    def __str__(self):
        return f"Certificate for {self.chai.name} - {self.certificate_number}"