from datetime import UTC

from rest_framework import serializers


class HorizonBoundsOutputSerializer(serializers.Serializer):
	lower_elevation_degrees = serializers.ListField(child=serializers.FloatField())
	upper_elevation_degrees = serializers.ListField(child=serializers.FloatField())


class HorizonOutputSerializer(serializers.Serializer):
	azimuth_offset_degrees = serializers.FloatField()
	bounds = HorizonBoundsOutputSerializer(allow_null=True)


class HorizonDirectionOutputSerializer(serializers.Serializer):
	elevation_degrees = serializers.FloatField()
	azimuth_degrees = serializers.FloatField()


class LocationHorizonOutputSerializer(HorizonOutputSerializer):
	dataset_id = serializers.IntegerField()
	timestamp = serializers.DateTimeField(default_timezone=UTC)
	latitude = serializers.FloatField()
	longitude = serializers.FloatField()
	sun = HorizonDirectionOutputSerializer()
	earth = HorizonDirectionOutputSerializer()
