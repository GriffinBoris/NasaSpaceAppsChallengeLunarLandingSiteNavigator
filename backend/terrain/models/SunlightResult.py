from core.base_models import ProjectBaseModel
from django.db import models
from django.utils.translation import gettext_lazy


class SunlightResult(ProjectBaseModel):
	class Meta:
		constraints = [
			models.UniqueConstraint(fields=('preparation', 'timestamp', 'version', 'ephemeris_signature'), name='unique_sunlight_result'),
		]

	preparation = models.ForeignKey(
		'terrain.SunlightPreparation',
		related_name='results',
		null=False,
		blank=False,
		verbose_name=gettext_lazy('Preparation'),
		on_delete=models.CASCADE,
	)
	timestamp = models.DateTimeField(null=False, blank=False, verbose_name=gettext_lazy('Timestamp'))
	version = models.PositiveSmallIntegerField(null=False, blank=False, verbose_name=gettext_lazy('Version'))
	ephemeris_signature = models.CharField(max_length=64, null=False, blank=False, verbose_name=gettext_lazy('Ephemeris signature'))
	visible_sun_fraction = models.FloatField(null=False, blank=False, verbose_name=gettext_lazy('Visible sun fraction'))
	thumbnail = models.JSONField(null=True, blank=False, verbose_name=gettext_lazy('Thumbnail'))
	result = models.JSONField(null=False, blank=False, verbose_name=gettext_lazy('Result'))
