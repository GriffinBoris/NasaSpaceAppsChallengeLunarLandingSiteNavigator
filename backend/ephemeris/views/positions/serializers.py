from datetime import UTC

from rest_framework import serializers


class EphemerisQuerySerializer(serializers.Serializer):
	timestamp = serializers.DateTimeField(default_timezone=UTC)


class CelestialBodyOutputSerializer(serializers.Serializer):
	position_km = serializers.ListField(child=serializers.FloatField(), min_length=3, max_length=3)
	radius_km = serializers.FloatField()


class EphemerisOutputSerializer(serializers.Serializer):
	timestamp = serializers.DateTimeField(default_timezone=UTC)
	frame = serializers.CharField()
	sun = CelestialBodyOutputSerializer()
	earth = CelestialBodyOutputSerializer()
