import pytest
from django.db import IntegrityError, transaction

from terrain.models.TerrainDataset import TerrainDataset
from terrain.models.TerrainTile import TerrainTile

pytestmark = pytest.mark.django_db


def test_tile_coordinates_are_unique_within_each_dataset():
	datasets = []

	for _ in range(2):
		dataset = TerrainDataset.objects.create(
			name='moon',
			frame='MOON_ME_DE421',
			reference_radius=1737400,
			tile_size=3,
			max_level=0,
			tile_count=1,
			refinements=[],
			sources=[],
		)
		datasets.append(dataset)
		TerrainTile.objects.create(dataset=dataset, face=0, level=0, tile_x=0, tile_y=0, data=b'heights')

	with pytest.raises(IntegrityError), transaction.atomic():
		TerrainTile.objects.create(dataset=datasets[0], face=0, level=0, tile_x=0, tile_y=0, data=b'duplicate')

	assert TerrainTile.objects.count() == 2
