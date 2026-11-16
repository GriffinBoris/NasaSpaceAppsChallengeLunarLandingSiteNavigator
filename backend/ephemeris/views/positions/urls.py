from django.urls import path

from ephemeris.views.positions.views import EphemerisView

app_name = 'positions'
urlpatterns = [
	path('', EphemerisView.as_view(), name='ephemeris-detail'),
]
