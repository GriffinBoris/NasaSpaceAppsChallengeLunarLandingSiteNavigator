from io import StringIO
from pathlib import Path

import numpy
import pytest
import rasterio
from django.core.management import CommandError, call_command
from django.urls import reverse
from rasterio.transform import from_bounds

from terrain.models.TerrainDataset import TerrainDataset
from terrain.models.TerrainTile import TerrainTile
from terrain.services.ingestion import TerrainIngestion
from terrain.services.raster import TerrainRaster, normalize_heights
from terrain.services.sources import GLOBAL_SOURCE_URL, PRESETS, TerrainPreset
from terrain.services.tile_encoding import decode_heights
from terrain.services.tile_grid import REFERENCE_RADIUS
from terrain.services.tile_reader import read_tile_heights

pytestmark = pytest.mark.django_db


@pytest.fixture
def terrain_root(settings, tmp_path):
	settings.TERRAIN_ROOT = tmp_path / 'terrain'
	return settings.TERRAIN_ROOT


def test_pds_scaling_does_not_add_reference_radius_twice():
	values = numpy.array([2000, -4000], dtype=numpy.int16)
	heights = normalize_heights(values, 0.5, REFERENCE_RADIUS, 'PDS')

	numpy.testing.assert_array_equal(heights, [1000, -2000])


def test_height_geotiff_applies_its_scale_and_offset():
	heights = normalize_heights(numpy.array([10]), 2, -5, 'GTiff')

	numpy.testing.assert_array_equal(heights, [15])


def test_global_source_wraps_longitude_and_joins_poles(global_source, open_raster):
	with rasterio.open(global_source, 'r+') as dataset:
		dataset.write(numpy.broadcast_to(numpy.arange(8) * 100, (4, 8)).astype(numpy.float32), 1)

	raster = open_raster(global_source, '', is_global=True)
	longitudes = numpy.array([-180.0, 180.0, 0.0, 135.0])
	latitudes = numpy.array([0.0, 0.0, 90.0, 90.0])
	samples = raster.sample(longitudes, latitudes)

	numpy.testing.assert_allclose(samples, [350, 350, 350, 350])


def test_ingestion_persists_catalog_and_matching_tiles(terrain_root, global_source, open_raster):
	raster = open_raster(global_source, 'https://example.com/global.tif', is_global=True)
	dataset = TerrainIngestion(raster, global_level=1, detail_level=1, tile_size=5).run('moon')
	dataset.refresh_from_db()
	tiles = list(dataset.tiles.all())

	assert dataset.tile_count == 30
	assert dataset.storage_format == TerrainDataset.StorageFormat.INT16_DELTA_GZIP
	assert dataset.status == TerrainDataset.Status.READY
	assert len(tiles) == 30
	assert not terrain_root.exists()
	assert len(dataset.refinements) == 6
	assert dataset.sources[0]['url'] == 'https://example.com/global.tif'
	assert len(dataset.sources[0]['files'][0]['sha256']) == 64

	for tile in tiles:
		heights = decode_heights(tile.data)
		numpy.testing.assert_array_equal(heights, numpy.full(25, 100))


def test_reingestion_publishes_new_catalog_and_preserves_old_tiles(client, terrain_root, global_source, open_raster):
	raster = open_raster(global_source, '', is_global=True)
	first = TerrainIngestion(raster, global_level=1, tile_size=5).run('moon')
	second = TerrainIngestion(raster, global_level=0, detail_level=0, tile_size=5).run('moon')

	assert first.pk != second.pk
	assert first.storage_key != second.storage_key
	assert TerrainDataset.objects.count() == 2
	assert first.tiles.count() == 30
	assert second.tiles.count() == 6
	assert client.get(reverse('terrain:dataset:terrain-detail')).data['storage_key'] == str(second.storage_key)

	response = client.get(
		reverse(
			'terrain:dataset:terrain-tile-detail',
			kwargs={'storage_key': first.storage_key, 'face': 0, 'level': 1, 'tile_x': 0, 'tile_y': 0},
		)
	)

	assert response.status_code == 200
	numpy.testing.assert_array_equal(numpy.frombuffer(response.content, dtype='<f4'), numpy.full(25, 100))


def test_loading_keeps_previous_catalog_and_tiles_available(client, terrain_root, global_source, open_raster):
	raster = open_raster(global_source, '', is_global=True)
	first = TerrainIngestion(raster, global_level=0, tile_size=5).run('moon')
	ingestion = TerrainIngestion(raster, global_level=1, tile_size=5)
	catalog_url = reverse('terrain:dataset:terrain-detail')
	tile_url = reverse(
		'terrain:dataset:terrain-tile-detail',
		kwargs={'storage_key': first.storage_key, 'face': 0, 'level': 0, 'tile_x': 0, 'tile_y': 0},
	)
	staging_tile_url = reverse(
		'terrain:dataset:terrain-tile-detail',
		kwargs={'storage_key': ingestion.storage_key, 'face': 0, 'level': 0, 'tile_x': 0, 'tile_y': 0},
	)
	checked_during_loading = False

	def progress(completed, total):
		nonlocal checked_during_loading

		if completed != 1:
			return

		checked_during_loading = True
		assert client.get(catalog_url).data['storage_key'] == str(first.storage_key)
		assert client.get(staging_tile_url).status_code == 404

		response = client.get(tile_url)

		assert response.status_code == 200
		numpy.testing.assert_array_equal(numpy.frombuffer(response.content, dtype='<f4'), numpy.full(25, 100))

	second = ingestion.run('moon', on_progress=progress)

	assert checked_during_loading
	assert client.get(catalog_url).data['storage_key'] == str(second.storage_key)


def test_failed_ingestion_preserves_previous_dataset(terrain_root, global_source, open_raster):
	raster = open_raster(global_source, '', is_global=True)
	first = TerrainIngestion(raster, global_level=0, detail_level=0, tile_size=5).run('moon')
	heights = numpy.full((4, 8), 100, dtype=numpy.float32)
	heights[1, 3] = numpy.nan

	with rasterio.open(global_source, 'r+') as dataset:
		dataset.write(heights, 1)

	raster = open_raster(global_source, '', is_global=True)
	ingestion = TerrainIngestion(raster, global_level=0, detail_level=0, tile_size=5)

	with pytest.raises(ValueError, match='missing heights'):
		ingestion.run('moon')

	first.refresh_from_db()
	assert first.tiles.count() == 6
	assert not TerrainDataset.objects.filter(storage_key=ingestion.storage_key).exists()
	assert TerrainDataset.objects.count() == 1


def test_failed_ingestion_removes_committed_batches_and_keeps_the_previous_version(client, global_source, open_raster):
	raster = open_raster(global_source, '', is_global=True)
	previous = TerrainIngestion(raster, global_level=0, tile_size=5).run('moon')
	ingestion = TerrainIngestion(raster, global_level=4, tile_size=5)
	catalog_url = reverse('terrain:dataset:terrain-detail')

	def progress(completed, total):
		if completed != 1125:
			return

		loading = TerrainDataset.objects.get(storage_key=ingestion.storage_key)

		assert loading.status == TerrainDataset.Status.LOADING
		assert loading.tiles.count() == 1000
		assert client.get(catalog_url).data['storage_key'] == str(previous.storage_key)

		raise ValueError('Stop test import.')

	with pytest.raises(ValueError, match='Stop test import'):
		ingestion.run('moon', on_progress=progress)

	assert TerrainDataset.objects.count() == 1
	assert TerrainTile.objects.count() == 6
	assert client.get(catalog_url).data['storage_key'] == str(previous.storage_key)


def test_command_downloads_and_loads_a_resolution_with_percentage(terrain_root, global_source, monkeypatch, settings):
	settings.MEDIA_ROOT = terrain_root.parent / 'media'
	unrelated_source = settings.MEDIA_ROOT / 'sources' / 'unrelated.bin'
	unrelated_source.parent.mkdir(parents=True)
	unrelated_source.write_bytes(b'preserve')
	urls = []

	def download(url, directory, on_progress):
		urls.append(url)
		on_progress(0, 100)
		on_progress(100, 100)
		return global_source

	monkeypatch.setattr('terrain.management.commands.ingest_terrain.download_file', download)
	output = StringIO()

	call_command('ingest_terrain', '4', stdout=output)

	dataset = TerrainDataset.objects.get(name='moon')
	assert dataset.max_level == 2
	assert dataset.tile_count == 126
	assert dataset.sources[0]['url'] == f'{GLOBAL_SOURCE_URL}/LDEM_4.IMG'
	assert urls == [f'{GLOBAL_SOURCE_URL}/LDEM_4.LBL', f'{GLOBAL_SOURCE_URL}/LDEM_4.IMG']
	assert 'Loading terrain:   0%' in output.getvalue()
	assert 'Loading terrain: 100%' in output.getvalue()
	assert 'Loaded 126 tiles (4).' in output.getvalue()
	assert 'Compressed terrain payload:' in output.getvalue()
	assert global_source.is_file()
	assert unrelated_source.read_bytes() == b'preserve'


def test_command_keeps_downloaded_sources_when_tile_generation_fails(terrain_root, global_source, monkeypatch):
	with rasterio.open(global_source, 'r+') as source:
		heights = numpy.full((4, 8), 100, dtype=numpy.float32)
		heights[1, 3] = numpy.nan
		source.write(heights, 1)

	monkeypatch.setattr('terrain.management.commands.ingest_terrain.download_file', lambda url, directory, on_progress: global_source)

	with pytest.raises(CommandError, match='missing heights'):
		call_command('ingest_terrain', '4', delete_sources=True, stdout=StringIO())

	assert global_source.is_file()
	assert TerrainDataset.objects.count() == 0
	assert TerrainTile.objects.count() == 0
	assert not terrain_root.exists()


def test_repeated_loads_reuse_existing_downloads_and_keep_them_by_default(terrain_root, global_source, settings, monkeypatch):
	settings.MEDIA_ROOT = terrain_root.parent / 'media'
	source_directory = settings.MEDIA_ROOT / 'sources'
	source_directory.mkdir(parents=True)

	for suffix in ('LBL', 'IMG'):
		(source_directory / f'LDEM_4.{suffix}').write_bytes(global_source.read_bytes())

	def reject_network(*args, **kwargs):
		raise AssertionError('Cached source files must not be downloaded again.')

	monkeypatch.setattr('core.services.downloads.urlopen', reject_network)

	call_command('ingest_terrain', '4', stdout=StringIO())
	call_command('ingest_terrain', '4', stdout=StringIO())

	assert TerrainDataset.objects.count() == 2
	assert TerrainTile.objects.count() == 252
	assert (source_directory / 'retained/LDEM_4.IMG').is_file()
	assert (source_directory / 'retained/LDEM_4.LBL').is_file()


def test_command_closes_rasters_before_removing_downloaded_sources(terrain_root, global_source, monkeypatch):
	original_close = TerrainRaster.close
	closed = []

	def close(raster):
		assert global_source.is_file()
		original_close(raster)
		closed.append(raster.dataset.closed)

	monkeypatch.setattr('terrain.management.commands.ingest_terrain.download_file', lambda url, directory, on_progress: global_source)
	monkeypatch.setattr(TerrainRaster, 'close', close)

	call_command('ingest_terrain', '4', delete_sources=True, stdout=StringIO())

	assert closed == [True]
	assert not global_source.exists()


def test_command_defaults_to_the_high_resolution_global_source(terrain_root, global_source, monkeypatch):
	monkeypatch.setitem(PRESETS, '512', TerrainPreset(512, 0))
	requested_resolutions = []

	def download_global(command, pixels_per_degree):
		requested_resolutions.append(pixels_per_degree)
		command.source_paths.add(global_source)
		return global_source, GLOBAL_SOURCE_URL

	monkeypatch.setattr('terrain.management.commands.ingest_terrain.Command._download_global', download_global)

	call_command('ingest_terrain', stdout=StringIO())

	assert requested_resolutions == [512]
	assert TerrainDataset.objects.get(name='moon').storage_format == TerrainDataset.StorageFormat.INT16_DELTA_GZIP
	assert global_source.is_file()


def test_source_cleanup_failure_reports_publication_without_removing_the_dataset(terrain_root, global_source, monkeypatch):
	original_unlink = Path.unlink

	def unlink(path, *args, **kwargs):
		if path == global_source:
			raise PermissionError('Source is locked.')

		return original_unlink(path, *args, **kwargs)

	monkeypatch.setattr('terrain.management.commands.ingest_terrain.download_file', lambda url, directory, on_progress: global_source)
	monkeypatch.setattr(Path, 'unlink', unlink)

	with pytest.raises(CommandError, match='Terrain was published, but downloaded sources could not be removed'):
		call_command('ingest_terrain', '4', delete_sources=True, stdout=StringIO())

	dataset = TerrainDataset.objects.get(name='moon')

	assert global_source.is_file()
	numpy.testing.assert_array_equal(read_tile_heights(dataset, 0, 0, 0, 0), numpy.full(65 * 65, 100))


def test_south_pole_source_overrides_global_heights_only_in_its_coverage(terrain_root, global_source, south_pole_source, open_raster):
	global_raster = open_raster(global_source, '', is_global=True)
	detail = open_raster(south_pole_source, '', is_global=False)
	dataset = TerrainIngestion(global_raster, detail, global_level=0, detail_level=1, tile_size=5).run('moon')
	south = read_tile_heights(dataset, 3, 0, 0, 0).reshape(5, 5)
	north = read_tile_heights(dataset, 2, 0, 0, 0).reshape(5, 5)

	assert south[2, 2] == 800
	assert south[0, 0] == 100
	numpy.testing.assert_array_equal(north, numpy.full((5, 5), 100))
	assert dataset.refinements == ['3/0/0/0']


def test_non_global_source_is_rejected_before_generating_tiles(global_source, open_raster):
	with rasterio.open(global_source, 'r+') as dataset:
		dataset.transform = from_bounds(0, -45, 90, 45, 8, 4)

	with pytest.raises(ValueError, match='cover all longitudes'):
		open_raster(global_source, '', is_global=True)


def test_ingestion_progress_is_monotonic_and_finishes_after_publishing(terrain_root, global_source, open_raster):
	raster = open_raster(global_source, '', is_global=True)
	updates = []

	def progress(completed, total):
		updates.append((completed, total))

		if completed == total:
			assert TerrainDataset.objects.get(name='moon').tile_count == 30

	TerrainIngestion(raster, global_level=1, tile_size=5).run('moon', on_progress=progress)

	assert updates == [(completed, 31) for completed in range(32)]
