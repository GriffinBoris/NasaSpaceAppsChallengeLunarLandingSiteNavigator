from django.urls import include, path

app_name = 'terrain'
urlpatterns = [
	path('', include('terrain.views.features.urls')),
	path('', include('terrain.views.dataset.urls')),
	path('', include('terrain.views.illumination.urls')),
	path('', include('terrain.views.earth.urls')),
	path('', include('terrain.views.horizon.urls')),
	path('', include('terrain.views.selections.urls')),
	path('', include('terrain.views.studies.urls')),
]
