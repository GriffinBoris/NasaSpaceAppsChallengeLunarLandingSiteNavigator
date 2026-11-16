from datetime import UTC
from math import isfinite

from rest_framework import serializers

from terrain.models.SunlightSelection import SunlightSelection
from terrain.services.illumination_patch import MAXIMUM_RADIUS_METERS, MINIMUM_RADIUS_METERS


class SunlightSelectionInputSerializer(serializers.ModelSerializer):
	name = serializers.CharField(max_length=120)
	latitude = serializers.FloatField(min_value=-90, max_value=90)
	longitude = serializers.FloatField(min_value=-180, max_value=180)
	radius_meters = serializers.FloatField(allow_null=True, min_value=MINIMUM_RADIUS_METERS, max_value=MAXIMUM_RADIUS_METERS)

	class Meta:
		model = SunlightSelection
		fields = ('name', 'latitude', 'longitude', 'radius_meters')

	def validate(self, attributes):
		for field in ('latitude', 'longitude', 'radius_meters'):
			if field in attributes and attributes[field] is not None and not isfinite(attributes[field]):
				raise serializers.ValidationError({field: 'Enter a finite number.'})

		return attributes


class SunlightSelectionOutputSerializer(serializers.ModelSerializer):
	created_ts = serializers.DateTimeField(default_timezone=UTC)
	updated_ts = serializers.DateTimeField(default_timezone=UTC)

	class Meta:
		model = SunlightSelection
		fields = ('id', 'name', 'latitude', 'longitude', 'radius_meters', 'created_ts', 'updated_ts')
		read_only_fields = fields
