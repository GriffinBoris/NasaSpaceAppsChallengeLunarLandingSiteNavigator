from django.db import models
from django.utils.translation import gettext_lazy


class ProjectBaseModel(models.Model):
	created_ts = models.DateTimeField(auto_now_add=True, null=False, blank=True, verbose_name=gettext_lazy('Created time'))
	updated_ts = models.DateTimeField(auto_now=True, null=False, blank=True, verbose_name=gettext_lazy('Updated time'))

	class Meta:
		abstract = True
