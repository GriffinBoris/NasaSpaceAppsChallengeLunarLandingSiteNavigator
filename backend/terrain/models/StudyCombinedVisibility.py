from core.base_models import ProjectBaseModel
from django.db import models
from django.utils.translation import gettext_lazy


class StudyCombinedVisibility(ProjectBaseModel):
	class Meta:
		ordering = ('study_id', 'selection_id')
		constraints = [
			models.UniqueConstraint(fields=('study', 'selection_id'), name='unique_study_combined_visibility'),
		]

	study = models.ForeignKey(
		'terrain.SunlightStudy',
		related_name='combined_visibility',
		null=False,
		blank=False,
		verbose_name=gettext_lazy('Study'),
		on_delete=models.CASCADE,
	)
	selection_id = models.PositiveBigIntegerField(null=False, blank=False, verbose_name=gettext_lazy('Selection id'))
	preparation = models.ForeignKey(
		'terrain.SunlightPreparation', null=False, blank=False, verbose_name=gettext_lazy('Preparation'), on_delete=models.PROTECT
	)
	ephemeris_signature = models.CharField(max_length=64, null=False, blank=False, verbose_name=gettext_lazy('Ephemeris signature'))
	visible_seconds = models.JSONField(null=False, blank=False, verbose_name=gettext_lazy('Visible seconds'))
	checked_frames = models.PositiveIntegerField(default=0, null=False, blank=False, verbose_name=gettext_lazy('Checked frames'))
	checked_seconds = models.FloatField(default=0, null=False, blank=False, verbose_name=gettext_lazy('Checked seconds'))
