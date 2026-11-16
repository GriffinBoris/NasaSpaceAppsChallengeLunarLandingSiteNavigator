from core.base_views import ProjectBaseAPIView
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from ephemeris.services.positions import EphemerisTimeError, EphemerisUnavailable
from ephemeris.views.exceptions import EphemerisServiceUnavailable
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from terrain.models.TerrainDataset import TerrainDataset
from terrain.services.illumination import calculate_illumination
from terrain.services.illumination_patch import iter_illumination_patch
from terrain.services.terrain_surface import TerrainAnalysisUnavailable
from terrain.views.illumination.serializers import (
	IlluminationOutputSerializer,
	IlluminationPatchOutputSerializer,
	IlluminationPatchQuerySerializer,
	IlluminationQuerySerializer,
)
from terrain.views.illumination.streaming import stream_illumination


class IlluminationView(ProjectBaseAPIView):
	serializer_class = IlluminationOutputSerializer

	calculation = staticmethod(calculate_illumination)

	def get(self, request, dataset_id):
		dataset = get_object_or_404(TerrainDataset.objects.exclude(status=TerrainDataset.Status.LOADING), pk=dataset_id)
		query = IlluminationQuerySerializer(data=request.query_params)
		query.is_valid(raise_exception=True)

		try:
			result = self.calculation(dataset, **query.validated_data)
		except EphemerisTimeError as error:
			raise ValidationError({'timestamp': str(error)}) from error
		except EphemerisUnavailable as error:
			raise EphemerisServiceUnavailable(str(error)) from error
		except TerrainAnalysisUnavailable as error:
			raise ValidationError({'dataset_id': str(error)}) from error

		return Response(self.serializer_class(result).data)


class IlluminationPatchView(ProjectBaseAPIView):
	result_serializer = IlluminationPatchOutputSerializer

	calculation = staticmethod(iter_illumination_patch)

	def get(self, request, dataset_id):
		dataset = get_object_or_404(TerrainDataset.objects.exclude(status=TerrainDataset.Status.LOADING), pk=dataset_id)
		query = IlluminationPatchQuerySerializer(data=request.query_params)
		query.is_valid(raise_exception=True)

		events = self.calculation(dataset, **query.validated_data)
		response = StreamingHttpResponse(stream_illumination(events, self.result_serializer), content_type='application/x-ndjson')
		response['Cache-Control'] = 'no-store'

		return response
