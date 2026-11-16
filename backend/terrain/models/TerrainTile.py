from core.base_models import ProjectBaseModel
from django.db import models
from django.utils.translation import gettext_lazy


class TerrainTile(ProjectBaseModel):
	class Meta:
		ordering = ('dataset_id', 'face', 'level', 'tile_x', 'tile_y')
		constraints = [
			models.UniqueConstraint(fields=('dataset', 'face', 'level', 'tile_x', 'tile_y'), name='unique_terrain_tile'),
		]

	dataset = models.ForeignKey(
		'terrain.TerrainDataset', related_name='tiles', null=False, blank=False, verbose_name=gettext_lazy('Dataset'), on_delete=models.CASCADE
	)
	face = models.PositiveSmallIntegerField(null=False, blank=False, verbose_name=gettext_lazy('Face'))
	level = models.PositiveSmallIntegerField(null=False, blank=False, verbose_name=gettext_lazy('Level'))
	tile_x = models.PositiveIntegerField(null=False, blank=False, verbose_name=gettext_lazy('Tile x'))
	tile_y = models.PositiveIntegerField(null=False, blank=False, verbose_name=gettext_lazy('Tile y'))
	data = models.BinaryField(null=False, blank=False, verbose_name=gettext_lazy('Data'))

	def __str__(self):
		return f'{self.dataset_id}: {self.face}/{self.level}/{self.tile_x}/{self.tile_y}'
