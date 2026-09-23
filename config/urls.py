"""URL configuration for the Maison backend."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('products.urls')),
    path('api/', include('contact.urls')),
]

if settings.DEBUG:
    # In production WhiteNoise serves these (see config/wsgi.py), or R2 does.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
