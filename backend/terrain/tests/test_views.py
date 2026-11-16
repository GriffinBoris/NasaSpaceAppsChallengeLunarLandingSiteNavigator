import numpy
import pytest
from django.urls import reverse

from terrain.models.TerrainDataset import TerrainDataset
from terrain.models.TerrainTile import TerrainTile
from terrain.services.tile_encoding import encode_heights

pytestmark = pytest.mark.django_db


@pytest.fixture
def dataset(settings, tmp_path):
	settings.TERRAIN_ROOT = tmp_path
	dataset = TerrainDataset.objects.create(
		name='moon',
		status=TerrainDataset.Status.READY,
		frame='MOON_ME_DE421',
		reference_radius=1737400,
		tile_size=3,
		max_level=1,
		tile_count=1,
		refinements=[],
		sources=[],
	)
	TerrainTile.objects.create(dataset=dataset, face=0, level=0, tile_x=0, tile_y=0, data=numpy.arange(9, dtype='<f4').tobytes())

	return dataset


def test_catalog_is_public_and_contains_tile_contract(client, dataset):
	response = client.get(reverse('terrain:dataset:terrain-detail'))

	assert response.status_code == 200
	assert response.data['reference_radius'] == 1737400
	assert response.data['tile_size'] == 3
	assert response.data['tile_url_template'] == f'terrain/{dataset.storage_key}/{{face}}/{{level}}/{{x}}/{{y}}/'


def test_missing_catalog_returns_not_found(client):
	assert client.get(reverse('terrain:dataset:terrain-detail')).status_code == 404


def test_tile_returns_float_heights_with_cache_headers(client, dataset):
	response = client.get(
		reverse('terrain:dataset:terrain-tile-detail', kwargs={'storage_key': dataset.storage_key, 'face': 0, 'level': 0, 'tile_x': 0, 'tile_y': 0})
	)
	content = response.content

	assert response.status_code == 200
	assert response['Content-Type'] == 'application/octet-stream'
	assert 'immutable' in response['Cache-Control']
	numpy.testing.assert_array_equal(numpy.frombuffer(content, dtype='<f4'), numpy.arange(9))


def test_compact_tiles_are_served_as_float_heights_without_the_downloaded_sources(client, dataset, settings):
	dataset.storage_format = TerrainDataset.StorageFormat.INT16_DELTA_GZIP
	dataset.save(update_fields=['storage_format'])
	heights = numpy.array([-1000.2, -100, -0.26, 0, 0.26, 100, 1000.2, 5000, 10000], dtype=numpy.float32)
	tile = dataset.tiles.get()
	tile.data = encode_heights(heights)
	tile.save(update_fields=['data'])

	response = client.get(
		reverse('terrain:dataset:terrain-tile-detail', kwargs={'storage_key': dataset.storage_key, 'face': 0, 'level': 0, 'tile_x': 0, 'tile_y': 0})
	)

	assert response.status_code == 200
	assert response['Content-Type'] == 'application/octet-stream'
	assert 'immutable' in response['Cache-Control']
	numpy.testing.assert_array_equal(numpy.frombuffer(response.content, dtype='<f4'), [-1000, -100, -0.5, 0, 0.5, 100, 1000, 5000, 10000])


@pytest.mark.parametrize('path', ['6/0/0/0/', '0/2/0/0/', '0/0/1/0/', '0/1/0/0/'])
def test_invalid_or_missing_tile_returns_not_found(client, dataset, path):
	response = client.get(f'/api/terrain/{dataset.storage_key}/{path}')

	assert response.status_code == 404


def test_public_api_has_no_write_actions(client, dataset):
	assert client.post(reverse('terrain:dataset:terrain-detail'), {}).status_code == 405


def test_unpublished_tile_rows_are_not_exposed_by_the_public_api(client, dataset):
	dataset.status = TerrainDataset.Status.LOADING
	dataset.save(update_fields=['status'])

	assert dataset.tiles.count() == 1
	assert client.get(reverse('terrain:dataset:terrain-detail')).status_code == 404
	assert (
		client.get(
			reverse(
				'terrain:dataset:terrain-tile-detail', kwargs={'storage_key': dataset.storage_key, 'face': 0, 'level': 0, 'tile_x': 0, 'tile_y': 0}
			)
		).status_code
		== 404
	)


def test_existing_file_datasets_remain_readable_while_they_are_transferred(client, dataset, settings):
	dataset.status = TerrainDataset.Status.FILES
	dataset.save(update_fields=['status'])
	dataset.tiles.all().delete()
	path = settings.TERRAIN_ROOT / str(dataset.storage_key) / '0/0/0'
	path.mkdir(parents=True)
	numpy.arange(9, dtype='<f4').tofile(path / '0.bin')

	response = client.get(
		reverse('terrain:dataset:terrain-tile-detail', kwargs={'storage_key': dataset.storage_key, 'face': 0, 'level': 0, 'tile_x': 0, 'tile_y': 0})
	)

	assert response.status_code == 200
	numpy.testing.assert_array_equal(numpy.frombuffer(response.content, dtype='<f4'), numpy.arange(9))
