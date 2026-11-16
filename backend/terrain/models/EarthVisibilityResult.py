from core.base_models import ProjectBaseModel
from django.db import models
from django.utils.translation import gettext_lazy


class EarthVisibilityResult(ProjectBaseModel):
	class Meta:
		constraints = [
			models.UniqueConstraint(fields=('preparation', 'timestamp', 'version', 'ephemeris_signature'), name='unique_earth_visibility_result'),
		]

	preparation = models.ForeignKey(
		'terrain.SunlightPreparation',
		related_name='earth_results',
		null=False,
		blank=False,
		verbose_name=gettext_lazy('Preparation'),
		on_delete=models.CASCADE,
	)
	timestamp = models.DateTimeField(null=False, blank=False, verbose_name=gettext_lazy('Timestamp'))
	version = models.PositiveSmallIntegerField(null=False, blank=False, verbose_name=gettext_lazy('Version'))
	ephemeris_signature = models.CharField(max_length=64, null=False, blank=False, verbose_name=gettext_lazy('Ephemeris signature'))
	visible_earth_fraction = models.FloatField(null=False, blank=False, verbose_name=gettext_lazy('Visible earth fraction'))
	earth_center_visible = models.BooleanField(null=False, blank=False, verbose_name=gettext_lazy('Earth center visible'))
	thumbnail = models.JSONField(null=True, blank=False, verbose_name=gettext_lazy('Thumbnail'))
	result = models.JSONField(null=False, blank=False, verbose_name=gettext_lazy('Result'))
