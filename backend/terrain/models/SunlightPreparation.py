from core.base_models import ProjectBaseModel
from django.db import models
from django.utils.translation import gettext_lazy


class SunlightPreparation(ProjectBaseModel):
	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=('dataset', 'latitude', 'longitude', 'radius_meters', 'grid_size', 'version'), name='unique_sunlight_preparation'
			),
		]

	dataset = models.ForeignKey(
		'terrain.TerrainDataset',
		related_name='sunlight_preparations',
		null=False,
		blank=False,
		verbose_name=gettext_lazy('Dataset'),
		on_delete=models.CASCADE,
	)
	latitude = models.FloatField(null=False, blank=False, verbose_name=gettext_lazy('Latitude'))
	longitude = models.FloatField(null=False, blank=False, verbose_name=gettext_lazy('Longitude'))
	radius_meters = models.FloatField(null=False, blank=False, verbose_name=gettext_lazy('Radius meters'))
	grid_size = models.PositiveSmallIntegerField(null=False, blank=False, verbose_name=gettext_lazy('Grid size'))
	version = models.PositiveSmallIntegerField(null=False, blank=False, verbose_name=gettext_lazy('Version'))
	samples = models.JSONField(null=False, blank=False, verbose_name=gettext_lazy('Samples'))
