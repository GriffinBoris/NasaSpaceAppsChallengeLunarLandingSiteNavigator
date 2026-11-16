from datetime import UTC

from rest_framework import serializers

from terrain.services.illumination_patch import DEFAULT_RADIUS_METERS, MAXIMUM_RADIUS_METERS, MINIMUM_RADIUS_METERS


class IlluminationQuerySerializer(serializers.Serializer):
	timestamp = serializers.DateTimeField(default_timezone=UTC)
	latitude = serializers.FloatField(min_value=-90, max_value=90)
	longitude = serializers.FloatField(min_value=-180, max_value=180)


class IlluminationPatchQuerySerializer(IlluminationQuerySerializer):
	radius_meters = serializers.FloatField(default=DEFAULT_RADIUS_METERS, min_value=MINIMUM_RADIUS_METERS, max_value=MAXIMUM_RADIUS_METERS)


class IlluminationOutputSerializer(serializers.Serializer):
	dataset_id = serializers.IntegerField()
	timestamp = serializers.DateTimeField(default_timezone=UTC)
	latitude = serializers.FloatField()
	longitude = serializers.FloatField()
	frame = serializers.CharField()
	elevation_meters = serializers.FloatField()
	analysis_level = serializers.IntegerField()
	sun_elevation_degrees = serializers.FloatField()
	sun_azimuth_degrees = serializers.FloatField()
	sun_angular_radius_degrees = serializers.FloatField()
	visible_sun_fraction = serializers.FloatField()
	disk_sample_count = serializers.IntegerField()
	sampling_converged = serializers.BooleanField()
	fraction_tolerance = serializers.FloatField()


class IlluminationPatchPointOutputSerializer(serializers.Serializer):
	visible_sun_fraction = serializers.FloatField()
	sampling_converged = serializers.BooleanField()


class IlluminationPatchOutputSerializer(serializers.Serializer):
	center = IlluminationOutputSerializer()
	grid_size = serializers.IntegerField()
	radius_meters = serializers.FloatField()
	spacing_meters = serializers.FloatField()
	points = serializers.ListField(child=IlluminationPatchPointOutputSerializer(allow_null=True))
