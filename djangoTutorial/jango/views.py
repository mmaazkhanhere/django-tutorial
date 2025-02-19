from django.shortcuts import render

# Create your views here.
def jango(request):
    return render(request, 'jango/all_tutorial.html')