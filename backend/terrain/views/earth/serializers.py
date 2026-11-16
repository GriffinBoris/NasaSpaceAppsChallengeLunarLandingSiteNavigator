from datetime import UTC

from rest_framework import serializers


class EarthVisibilityOutputSerializer(serializers.Serializer):
	dataset_id = serializers.IntegerField()
	timestamp = serializers.DateTimeField(default_timezone=UTC)
	latitude = serializers.FloatField()
	longitude = serializers.FloatField()
	frame = serializers.CharField()
	elevation_meters = serializers.FloatField()
	analysis_level = serializers.IntegerField()
	earth_elevation_degrees = serializers.FloatField()
	earth_azimuth_degrees = serializers.FloatField()
	earth_angular_radius_degrees = serializers.FloatField()
	visible_earth_fraction = serializers.FloatField()
	earth_center_visible = serializers.BooleanField()
	disk_sample_count = serializers.IntegerField()
	sampling_converged = serializers.BooleanField()
	fraction_tolerance = serializers.FloatField()


class EarthVisibilityPatchPointOutputSerializer(serializers.Serializer):
	visible_earth_fraction = serializers.FloatField()
	earth_center_visible = serializers.BooleanField()
	sampling_converged = serializers.BooleanField()


class EarthVisibilityPatchOutputSerializer(serializers.Serializer):
	center = EarthVisibilityOutputSerializer()
	grid_size = serializers.IntegerField()
	radius_meters = serializers.FloatField()
	spacing_meters = serializers.FloatField()
	points = serializers.ListField(child=EarthVisibilityPatchPointOutputSerializer(allow_null=True))
