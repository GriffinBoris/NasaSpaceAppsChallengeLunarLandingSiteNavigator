from django.urls import path

from terrain.views.dataset.views import TerrainDatasetView, TerrainTileView

app_name = 'dataset'
urlpatterns = [
	path('', TerrainDatasetView.as_view(), name='terrain-detail'),
	path('versions/<int:dataset_id>/', TerrainDatasetView.as_view(), name='terrain-version-detail'),
	path('<uuid:storage_key>/<int:face>/<int:level>/<int:tile_x>/<int:tile_y>/', TerrainTileView.as_view(), name='terrain-tile-detail'),
]
