from io import StringIO

import numpy
import pytest
from django.core.management import CommandError, call_command
from django.urls import reverse

from terrain.models.TerrainDataset import TerrainDataset
from terrain.models.TerrainTile import TerrainTile
from terrain.services.file_import import import_file_tiles
from terrain.services.tile_encoding import decode_heights, encode_heights

pytestmark = pytest.mark.django_db


@pytest.fixture
def file_dataset(settings, tmp_path):
	settings.TERRAIN_ROOT = tmp_path
	dataset = TerrainDataset.objects.create(
		name='moon',
		frame='MOON_ME_DE421',
		reference_radius=1737400,
		tile_size=3,
		max_level=0,
		tile_count=6,
		refinements=[],
		sources=[],
	)

	for face in range(6):
		directory = tmp_path / str(dataset.storage_key) / str(face) / '0/0'
		directory.mkdir(parents=True)
		numpy.full(9, face * 100 + 0.2, dtype='<f4').tofile(directory / '0.bin')

	return dataset


@pytest.mark.parametrize('storage_format', TerrainDataset.StorageFormat.values)
def test_file_import_creates_tile_rows_without_resampling_and_retains_originals(file_dataset, settings, storage_format, client):
	file_dataset.storage_format = storage_format
	file_dataset.save(update_fields=['storage_format'])
	directory = settings.TERRAIN_ROOT / str(file_dataset.storage_key)

	if storage_format == TerrainDataset.StorageFormat.INT16_DELTA_GZIP:
		for path in directory.rglob('*.bin'):
			path.write_bytes(encode_heights(numpy.fromfile(path, dtype='<f4')))

	updates = []

	def progress(completed, total):
		updates.append((completed, total))

		if completed < total:
			response = client.get(reverse('terrain:dataset:terrain-detail'))
			assert response.data['storage_key'] == str(file_dataset.storage_key)

	dataset = import_file_tiles(file_dataset, progress)

	assert dataset.pk != file_dataset.pk
	assert dataset.status == TerrainDataset.Status.READY
	assert dataset.tiles.count() == 6
	assert updates == [(completed, 7) for completed in range(8)]
	assert client.get(reverse('terrain:dataset:terrain-detail')).data['storage_key'] == str(dataset.storage_key)

	for tile in dataset.tiles.all():
		numpy.testing.assert_array_equal(decode_heights(tile.data), numpy.full(9, tile.face * 100))
		original_path = directory / str(tile.face) / '0/0/0.bin'
		assert original_path.is_file()

		if storage_format == TerrainDataset.StorageFormat.INT16_DELTA_GZIP:
			assert tile.data == original_path.read_bytes()


def test_incomplete_file_import_does_not_publish_or_leave_partial_rows(file_dataset, settings):
	path = settings.TERRAIN_ROOT / str(file_dataset.storage_key) / '4/0/0/0.bin'
	path.unlink()

	with pytest.raises(FileNotFoundError):
		import_file_tiles(file_dataset, lambda completed, total: None)

	assert list(TerrainDataset.objects.values_list('pk', flat=True)) == [file_dataset.pk]
	assert TerrainTile.objects.count() == 0


def test_file_import_rejects_mismatched_catalog_count(file_dataset):
	file_dataset.tile_count = 7
	file_dataset.save(update_fields=['tile_count'])

	with pytest.raises(ValueError, match='count does not match'):
		import_file_tiles(file_dataset, lambda completed, total: None)

	assert TerrainDataset.objects.count() == 1
	assert TerrainTile.objects.count() == 0


def test_file_transfer_command_requires_a_specific_existing_dataset(file_dataset):
	with pytest.raises(CommandError, match='does not exist'):
		call_command('import_terrain_tiles', file_dataset.pk + 1, stdout=StringIO())

	output = StringIO()
	call_command('import_terrain_tiles', file_dataset.pk, stdout=output)

	assert 'Stored 6 tile rows' in output.getvalue()
	assert 'Original files were retained' in output.getvalue()
	assert TerrainTile.objects.count() == 6


def test_database_versions_cannot_be_imported_as_files(file_dataset):
	dataset = import_file_tiles(file_dataset, lambda completed, total: None)

	with pytest.raises(ValueError, match='already uses database'):
		import_file_tiles(dataset, lambda completed, total: None)

	assert TerrainDataset.objects.count() == 2
