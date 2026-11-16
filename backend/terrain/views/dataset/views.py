from core.base_views import ProjectBaseAPIView
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

from terrain.models.TerrainDataset import TerrainDataset
from terrain.models.TerrainTile import TerrainTile
from terrain.services.tile_reader import read_tile_heights
from terrain.views.dataset.serializers import TerrainDatasetOutputSerializer


class TerrainDatasetView(ProjectBaseAPIView):
	def get(self, request, dataset_id=None):
		if dataset_id is not None:
			dataset = get_object_or_404(TerrainDataset.objects.exclude(status=TerrainDataset.Status.LOADING), pk=dataset_id)
			return Response(TerrainDatasetOutputSerializer(dataset).data)

		dataset = TerrainDataset.objects.filter(name='moon').exclude(status=TerrainDataset.Status.LOADING).first()

		if dataset is None:
			raise Http404('No terrain dataset has been loaded.')

		return Response(TerrainDatasetOutputSerializer(dataset).data)


class TerrainTileView(ProjectBaseAPIView):
	def get(self, request, storage_key, face, level, tile_x, tile_y):
		published_datasets = TerrainDataset.objects.exclude(status=TerrainDataset.Status.LOADING).defer('refinements', 'sources')
		dataset = get_object_or_404(published_datasets, storage_key=storage_key)
		if face > 5 or level > dataset.max_level:
			raise Http404('Terrain tile does not exist.')

		if tile_x >= 2**level or tile_y >= 2**level:
			raise Http404('Terrain tile does not exist.')

		try:
			heights = read_tile_heights(dataset, face, level, tile_x, tile_y)
		except (FileNotFoundError, TerrainTile.DoesNotExist) as error:
			raise Http404('Terrain tile does not exist.') from error

		response = HttpResponse(heights.tobytes(), content_type='application/octet-stream')
		response['Cache-Control'] = 'public, max-age=31536000, immutable'
		return response
