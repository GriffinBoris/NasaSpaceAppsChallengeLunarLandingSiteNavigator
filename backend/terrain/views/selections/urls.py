from django.urls import path

from terrain.views.selections.views import SunlightSelectionDetailView, SunlightSelectionListView

app_name = 'selections'
urlpatterns = [
	path('selections/', SunlightSelectionListView.as_view(), name='sunlight-selection-list'),
	path('selections/<int:selection_id>/', SunlightSelectionDetailView.as_view(), name='sunlight-selection-detail'),
]
