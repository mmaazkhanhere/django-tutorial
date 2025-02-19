
from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path("jango/", include("jango.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
