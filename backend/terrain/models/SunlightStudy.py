from core.base_models import ProjectBaseModel
from django.db import models
from django.utils.translation import gettext_lazy


class SunlightStudy(ProjectBaseModel):
	class Meta:
		ordering = ('-id',)

	class Status(models.TextChoices):
		PENDING = 'pending', gettext_lazy('Pending')
		QUEUED = 'queued', gettext_lazy('Queued')
		RUNNING = 'running', gettext_lazy('Running')
		STOPPING = 'stopping', gettext_lazy('Stopping')
		STOPPED = 'stopped', gettext_lazy('Stopped')
		FAILED = 'failed', gettext_lazy('Failed')
		COMPLETE = 'complete', gettext_lazy('Complete')

	class WorkerCount(models.IntegerChoices):
		ONE = 1, gettext_lazy('1 worker')
		TWO = 2, gettext_lazy('2 workers')
		FOUR = 4, gettext_lazy('4 workers')
		EIGHT = 8, gettext_lazy('8 workers')
		SIXTEEN = 16, gettext_lazy('16 workers')

	name = models.TextField(null=False, blank=False, verbose_name=gettext_lazy('Name'))
	dataset = models.ForeignKey(
		'terrain.TerrainDataset',
		related_name='sunlight_studies',
		null=False,
		blank=False,
		verbose_name=gettext_lazy('Dataset'),
		on_delete=models.PROTECT,
	)
	selections = models.JSONField(null=False, blank=False, verbose_name=gettext_lazy('Selections'))
	start_time = models.DateTimeField(null=False, blank=False, verbose_name=gettext_lazy('Start time'))
	end_time = models.DateTimeField(null=False, blank=False, verbose_name=gettext_lazy('End time'))
	step_seconds = models.PositiveIntegerField(null=False, blank=False, verbose_name=gettext_lazy('Step seconds'))
	worker_count = models.PositiveSmallIntegerField(
		choices=WorkerCount.choices, default=WorkerCount.FOUR, null=False, blank=False, verbose_name=gettext_lazy('Worker count')
	)
	expected_frames = models.PositiveIntegerField(null=False, blank=False, verbose_name=gettext_lazy('Expected frames'))
	status = models.TextField(choices=Status.choices, default=Status.PENDING, null=False, blank=False, verbose_name=gettext_lazy('Status'))
	run_id = models.UUIDField(editable=False, null=True, blank=False, verbose_name=gettext_lazy('Run id'))
	progress = models.JSONField(null=True, blank=True, verbose_name=gettext_lazy('Progress'))
	error_message = models.TextField(null=False, blank=True, verbose_name=gettext_lazy('Error message'))
	result_revision = models.PositiveBigIntegerField(default=0, null=False, blank=False, verbose_name=gettext_lazy('Result revision'))
	reset_revision = models.PositiveBigIntegerField(default=0, null=False, blank=False, verbose_name=gettext_lazy('Reset revision'))

	def __str__(self):
		return self.name

	def complete_frames(self):
		return self.frames.filter(visible_sun_fraction__isnull=False, cached_earth_result__isnull=False)
