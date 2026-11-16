from django.urls import path

from terrain.views.features.views import LunarFeatureLabelsView, LunarFeatureSearchView

app_name = 'features'
urlpatterns = [
	path('features/', LunarFeatureSearchView.as_view(), name='lunar-feature-search'),
	path('features/labels/', LunarFeatureLabelsView.as_view(), name='lunar-feature-labels'),
]
