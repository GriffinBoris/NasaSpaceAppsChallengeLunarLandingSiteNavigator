from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core.views.index.views import index

urlpatterns = [
	path('', index, name='index'),
	path('admin/', admin.site.urls),
	path('api/terrain/', include('terrain.urls')),
	path('api/ephemeris/', include('ephemeris.urls')),
]

if settings.DEBUG:
	urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
