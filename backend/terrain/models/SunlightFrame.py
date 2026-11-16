from core.base_models import ProjectBaseModel
from django.db import models
from django.utils.translation import gettext_lazy


class SunlightFrame(ProjectBaseModel):
	class Meta:
		ordering = ('timestamp', 'selection_id')
		constraints = [
			models.UniqueConstraint(fields=('study', 'selection_id', 'timestamp'), name='unique_sunlight_frame'),
		]

	study = models.ForeignKey(
		'terrain.SunlightStudy', related_name='frames', null=False, blank=False, verbose_name=gettext_lazy('Study'), on_delete=models.CASCADE
	)
	selection_id = models.PositiveBigIntegerField(null=False, blank=False, verbose_name=gettext_lazy('Selection id'))
	timestamp = models.DateTimeField(null=False, blank=False, verbose_name=gettext_lazy('Timestamp'))
	visible_sun_fraction = models.FloatField(null=True, blank=False, verbose_name=gettext_lazy('Visible sun fraction'))
	thumbnail = models.JSONField(null=True, blank=False, verbose_name=gettext_lazy('Thumbnail'))
	result = models.JSONField(null=True, blank=False, verbose_name=gettext_lazy('Result'))
	cached_result = models.ForeignKey(
		'terrain.SunlightResult', related_name='frames', null=True, blank=True, verbose_name=gettext_lazy('Cached result'), on_delete=models.PROTECT
	)
	cached_earth_result = models.ForeignKey(
		'terrain.EarthVisibilityResult',
		related_name='frames',
		null=True,
		blank=True,
		verbose_name=gettext_lazy('Cached earth result'),
		on_delete=models.PROTECT,
	)
	visible_earth_fraction = models.FloatField(null=True, blank=False, verbose_name=gettext_lazy('Visible earth fraction'))
	earth_center_visible = models.BooleanField(null=True, blank=False, verbose_name=gettext_lazy('Earth center visible'))
	joint_visible_share = models.FloatField(null=True, blank=False, verbose_name=gettext_lazy('Joint visible share'))
	joint_grid = models.JSONField(null=True, blank=False, verbose_name=gettext_lazy('Joint grid'))
	result_revision = models.PositiveBigIntegerField(db_index=True, default=0, null=False, blank=False, verbose_name=gettext_lazy('Result revision'))

	@property
	def calculation_result(self):
		if self.cached_result_id is not None:
			return self.cached_result.result

		return self.result
