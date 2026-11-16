from core.base_views import ProjectBaseAPIView
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from ephemeris.services.positions import EphemerisTimeError, EphemerisUnavailable, calculate_positions
from ephemeris.views.exceptions import EphemerisServiceUnavailable
from ephemeris.views.positions.serializers import EphemerisOutputSerializer, EphemerisQuerySerializer


class EphemerisView(ProjectBaseAPIView):
	def get(self, request):
		query = EphemerisQuerySerializer(data=request.query_params)
		query.is_valid(raise_exception=True)

		try:
			positions = calculate_positions(query.validated_data['timestamp'])
		except EphemerisTimeError as error:
			raise ValidationError({'timestamp': str(error)}) from error
		except EphemerisUnavailable as error:
			raise EphemerisServiceUnavailable(str(error)) from error

		return Response(EphemerisOutputSerializer(positions).data)
