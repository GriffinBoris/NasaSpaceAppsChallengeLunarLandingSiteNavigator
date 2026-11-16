from core.base_models import ProjectBaseModel
from django.db import models
from django.utils.translation import gettext_lazy


class SunlightHorizon(ProjectBaseModel):
	class Meta:
		constraints = [
			models.UniqueConstraint(fields=('dataset', 'latitude', 'longitude', 'version'), name='unique_sunlight_horizon'),
		]

	dataset = models.ForeignKey(
		'terrain.TerrainDataset',
		related_name='sunlight_horizons',
		null=False,
		blank=False,
		verbose_name=gettext_lazy('Dataset'),
		on_delete=models.CASCADE,
	)
	latitude = models.FloatField(null=False, blank=False, verbose_name=gettext_lazy('Latitude'))
	longitude = models.FloatField(null=False, blank=False, verbose_name=gettext_lazy('Longitude'))
	version = models.PositiveSmallIntegerField(null=False, blank=False, verbose_name=gettext_lazy('Version'))
	data = models.BinaryField(null=False, blank=False, verbose_name=gettext_lazy('Data'))
