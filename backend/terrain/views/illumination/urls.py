from django.urls import path

from terrain.views.illumination.views import IlluminationPatchView, IlluminationView

app_name = 'illumination'
urlpatterns = [
	path('<int:dataset_id>/illumination/', IlluminationView.as_view(), name='terrain-illumination-detail'),
	path('<int:dataset_id>/illumination/patch/', IlluminationPatchView.as_view(), name='terrain-illumination-patch-detail'),
]
