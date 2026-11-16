from math import asin, cos, degrees, radians, sin

from core.base_views import ProjectBaseAPIView
from django.db.models import Q
from rest_framework.response import Response

from terrain.models.LunarFeature import LunarFeature
from terrain.views.features.serializers import LunarFeatureLabelsQuerySerializer, LunarFeatureOutputSerializer, LunarFeatureSearchQuerySerializer


class LunarFeatureSearchView(ProjectBaseAPIView):
	def get(self, request):
		serializer = LunarFeatureSearchQuerySerializer(data=request.query_params)
		serializer.is_valid(raise_exception=True)
		query = serializer.validated_data['q']
		features = LunarFeature.objects.filter(approval_status='Adopted by IAU')
		catalog_loaded = LunarFeature.objects.exists()

		if query:
			features = features.filter(
				Q(name__icontains=query) | Q(clean_name__icontains=query) | Q(origin__icontains=query),
			)[:20]
		else:
			features = features.none()

		return Response({'features': LunarFeatureOutputSerializer(features, many=True).data, 'catalog_loaded': catalog_loaded})


class LunarFeatureLabelsView(ProjectBaseAPIView):
	def get(self, request):
		serializer = LunarFeatureLabelsQuerySerializer(data=request.query_params)
		serializer.is_valid(raise_exception=True)
		latitude = serializer.validated_data['latitude']
		longitude = serializer.validated_data['longitude']
		radius_degrees = serializer.validated_data['radius_degrees']
		features = LunarFeature.objects.filter(
			approval_status='Adopted by IAU',
			diameter_km__gte=serializer.validated_data['minimum_diameter_km'],
			latitude__gte=max(-90, latitude - radius_degrees),
			latitude__lte=min(90, latitude + radius_degrees),
		)

		if abs(latitude) + radius_degrees < 90:
			longitude_radius = degrees(asin(min(1, sin(radians(radius_degrees)) / cos(radians(latitude)))))
			western_longitude = longitude - longitude_radius
			eastern_longitude = longitude + longitude_radius

			if western_longitude < -180:
				features = features.filter(Q(longitude__gte=western_longitude + 360) | Q(longitude__lte=eastern_longitude))
			elif eastern_longitude > 180:
				features = features.filter(Q(longitude__gte=western_longitude) | Q(longitude__lte=eastern_longitude - 360))
			else:
				features = features.filter(longitude__range=(western_longitude, eastern_longitude))

		features = features.order_by('-diameter_km', 'usgs_id')[:300]

		return Response(LunarFeatureOutputSerializer(features, many=True).data)
