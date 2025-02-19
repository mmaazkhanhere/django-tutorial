from django.shortcuts import render
from .models import ChaiVariety

# Create your views here.
def jango(request):
    chais = ChaiVariety.objects.all()
    return render(request, 'jango/all_tutorial.html', {'chais': chais})