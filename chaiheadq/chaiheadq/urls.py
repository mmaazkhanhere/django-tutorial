from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from django.urls import include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('tweet/', include('tweet.urls'))
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
