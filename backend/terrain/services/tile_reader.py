import numpy
from django.conf import settings

from terrain.models.TerrainDataset import TerrainDataset
from terrain.models.TerrainTile import TerrainTile
from terrain.services.tile_encoding import decode_heights


def read_tile_content(dataset, face, level, tile_x, tile_y):
	if dataset.status == TerrainDataset.Status.FILES:
		path = settings.TERRAIN_ROOT / str(dataset.storage_key) / str(face) / str(level) / str(tile_x) / f'{tile_y}.bin'
		return path.read_bytes()

	return TerrainTile.objects.values_list('data', flat=True).get(dataset=dataset, face=face, level=level, tile_x=tile_x, tile_y=tile_y)


def decode_tile_content(content, storage_format):
	if storage_format == TerrainDataset.StorageFormat.INT16_DELTA_GZIP:
		return decode_heights(content)

	return numpy.frombuffer(content, dtype='<f4')


def read_tile_heights(dataset, face, level, tile_x, tile_y):
	content = read_tile_content(dataset, face, level, tile_x, tile_y)

	return decode_tile_content(content, dataset.storage_format)
