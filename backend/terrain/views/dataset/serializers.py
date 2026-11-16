from rest_framework import serializers

from terrain.models.TerrainDataset import TerrainDataset


class TerrainDatasetOutputSerializer(serializers.ModelSerializer):
	tile_url_template = serializers.SerializerMethodField()

	class Meta:
		model = TerrainDataset
		fields = (
			'id',
			'name',
			'storage_key',
			'frame',
			'reference_radius',
			'tile_size',
			'max_level',
			'tile_count',
			'refinements',
			'sources',
			'tile_url_template',
		)
		read_only_fields = fields

	def get_tile_url_template(self, instance):
		return f'terrain/{instance.storage_key}/{{face}}/{{level}}/{{x}}/{{y}}/'
