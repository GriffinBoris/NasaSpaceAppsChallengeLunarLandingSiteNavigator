from django.urls import path

from terrain.views.horizon.views import LocationHorizonView

app_name = 'horizon'
urlpatterns = [
	path('<int:dataset_id>/horizon/', LocationHorizonView.as_view(), name='location-horizon-detail'),
]
