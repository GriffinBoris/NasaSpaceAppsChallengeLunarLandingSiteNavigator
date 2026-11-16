from django.urls import path

from terrain.views.earth.views import EarthVisibilityPatchView, EarthVisibilityView

app_name = 'earth'
urlpatterns = [
	path('<int:dataset_id>/earth/', EarthVisibilityView.as_view(), name='earth-visibility-detail'),
	path('<int:dataset_id>/earth/patch/', EarthVisibilityPatchView.as_view(), name='earth-visibility-patch-detail'),
]
