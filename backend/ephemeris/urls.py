from django.urls import include, path

app_name = 'ephemeris'
urlpatterns = [
	path('', include('ephemeris.views.positions.urls')),
]
