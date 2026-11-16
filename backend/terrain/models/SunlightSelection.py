from core.base_models import ProjectBaseModel
from django.db import models
from django.utils.translation import gettext_lazy


class SunlightSelection(ProjectBaseModel):
	class Meta:
		ordering = ('name', 'id')

	name = models.TextField(null=False, blank=False, verbose_name=gettext_lazy('Name'))
	latitude = models.FloatField(null=False, blank=False, verbose_name=gettext_lazy('Latitude'))
	longitude = models.FloatField(null=False, blank=False, verbose_name=gettext_lazy('Longitude'))
	radius_meters = models.FloatField(null=True, blank=True, verbose_name=gettext_lazy('Radius meters'))

	def __str__(self):
		return self.name
