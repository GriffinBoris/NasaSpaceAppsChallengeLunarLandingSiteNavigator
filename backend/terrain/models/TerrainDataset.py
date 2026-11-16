import uuid

from core.base_models import ProjectBaseModel
from django.db import models
from django.utils.translation import gettext_lazy


class TerrainDataset(ProjectBaseModel):
	class Meta:
		ordering = ('name', '-id')

	class StorageFormat(models.TextChoices):
		FLOAT32 = 'float32', gettext_lazy('Float32')
		INT16_DELTA_GZIP = 'int16-delta-gzip', gettext_lazy('Int16 delta + gzip')

	class Status(models.TextChoices):
		FILES = 'files', gettext_lazy('Legacy files')
		LOADING = 'loading', gettext_lazy('Loading')
		READY = 'ready', gettext_lazy('Ready')

	name = models.SlugField(null=False, blank=False, verbose_name=gettext_lazy('Name'))
	status = models.TextField(
		choices=Status.choices, db_default=Status.FILES, default=Status.FILES, null=False, blank=False, verbose_name=gettext_lazy('Status')
	)
	storage_key = models.UUIDField(unique=True, default=uuid.uuid4, null=False, blank=False, verbose_name=gettext_lazy('Storage key'))
	storage_format = models.TextField(
		choices=StorageFormat.choices, default=StorageFormat.FLOAT32, null=False, blank=False, verbose_name=gettext_lazy('Storage format')
	)
	frame = models.TextField(null=False, blank=False, verbose_name=gettext_lazy('Frame'))
	reference_radius = models.FloatField(null=False, blank=False, verbose_name=gettext_lazy('Reference radius'))
	tile_size = models.PositiveSmallIntegerField(null=False, blank=False, verbose_name=gettext_lazy('Tile size'))
	max_level = models.PositiveSmallIntegerField(null=False, blank=False, verbose_name=gettext_lazy('Max level'))
	tile_count = models.PositiveIntegerField(null=False, blank=False, verbose_name=gettext_lazy('Tile count'))
	refinements = models.JSONField(null=False, blank=False, verbose_name=gettext_lazy('Refinements'))
	sources = models.JSONField(null=False, blank=False, verbose_name=gettext_lazy('Sources'))

	def __str__(self):
		return self.name
