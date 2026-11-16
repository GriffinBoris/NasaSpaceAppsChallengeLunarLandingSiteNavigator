from core.base_models import ProjectBaseModel
from django.db import models
from django.utils.translation import gettext_lazy


class LunarFeature(ProjectBaseModel):
	class Meta:
		ordering = ('name', 'usgs_id')

	usgs_id = models.PositiveIntegerField(unique=True, null=False, blank=False, verbose_name=gettext_lazy('USGS ID'))
	name = models.TextField(db_index=True, null=False, blank=False, verbose_name=gettext_lazy('Name'))
	clean_name = models.TextField(db_index=True, null=False, blank=False, verbose_name=gettext_lazy('Clean name'))
	feature_type = models.TextField(null=False, blank=False, verbose_name=gettext_lazy('Feature type'))
	latitude = models.FloatField(null=False, blank=False, verbose_name=gettext_lazy('Latitude'))
	longitude = models.FloatField(null=False, blank=False, verbose_name=gettext_lazy('Longitude'))
	diameter_km = models.FloatField(null=True, blank=True, verbose_name=gettext_lazy('Diameter km'))
	origin = models.TextField(null=False, blank=True, verbose_name=gettext_lazy('Origin'))
	approval_status = models.TextField(null=False, blank=False, verbose_name=gettext_lazy('Approval status'))

	def __str__(self):
		return self.name

	@property
	def source_url(self):
		return f'https://planetarynames.wr.usgs.gov/Feature/{self.usgs_id}'
