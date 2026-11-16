from math import isfinite

from rest_framework import serializers

from terrain.models.LunarFeature import LunarFeature


class LunarFeatureSearchQuerySerializer(serializers.Serializer):
	q = serializers.CharField(max_length=120, min_length=2, allow_blank=True, default='')


class LunarFeatureOutputSerializer(serializers.ModelSerializer):
	english_name = serializers.SerializerMethodField()

	class Meta:
		model = LunarFeature
		fields = ('id', 'usgs_id', 'name', 'english_name', 'feature_type', 'latitude', 'longitude', 'diameter_km', 'source_url')
		read_only_fields = fields

	def get_english_name(self, instance):
		origin = instance.origin.strip().removeprefix('Latin for ')
		closing_quote = {'"': '"', '“': '”'}.get(origin[:1])

		if not closing_quote:
			return None

		english_name, separator, _ = origin[1:].partition(closing_quote)

		if not separator:
			return None

		return english_name.strip().rstrip('.,') or None


class LunarFeatureLabelsQuerySerializer(serializers.Serializer):
	latitude = serializers.FloatField(min_value=-90, max_value=90)
	longitude = serializers.FloatField(min_value=-180, max_value=180)
	radius_degrees = serializers.FloatField(min_value=0.001, max_value=90)
	minimum_diameter_km = serializers.FloatField(min_value=0)

	def validate(self, attributes):
		if not all(isfinite(value) for value in attributes.values()):
			raise serializers.ValidationError('Coordinates and sizes must be finite numbers.')

		return attributes
