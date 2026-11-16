from io import StringIO

import numpy
import pytest
import rasterio
from django.core.management import call_command
from rasterio.transform import from_bounds

from terrain.models.TerrainDataset import TerrainDataset
from terrain.services.mosaic import build_mosaic
from terrain.services.raster import TerrainRaster
from terrain.services.sources import GLOBAL_SOURCE_URL, PRESETS, TerrainPreset, global_source_filenames


@pytest.fixture
def quadrants(tmp_path):
	source_paths = []

	for row in range(2):
		for column in range(2):
			path = tmp_path / f'source_{row}_{column}.tif'
			left = -180 + column * 180
			top = 90 - row * 90

			with rasterio.open(
				path,
				'w',
				driver='GTiff',
				width=4,
				height=2,
				count=1,
				dtype='int16',
				crs='+proj=longlat +R=1737400 +no_defs',
				transform=from_bounds(left, top - 90, left + 180, top, 4, 2),
			) as dataset:
				dataset.write(numpy.full((2, 4), (row * 2 + column + 1) * 100, dtype=numpy.int16), 1)
				dataset.scales = (0.5,)

			source_paths.append(path)

	return source_paths


def test_mosaic_preserves_heights_and_interpolates_across_boundaries(quadrants, tmp_path):
	path = build_mosaic(quadrants, tmp_path / 'global.vrt')

	with TerrainRaster(path, GLOBAL_SOURCE_URL, is_global=True) as raster:
		longitudes = numpy.array([-90.0, 90.0, -90.0, 90.0, 0.0, 180.0])
		latitudes = numpy.array([45.0, 45.0, -45.0, -45.0, 0.0, 0.0])
		heights = raster.sample(longitudes, latitudes)

		numpy.testing.assert_array_equal(heights, [50, 100, 150, 200, 125, 125])
		assert {source['name'] for source in raster.metadata['files']} >= {path.name for path in quadrants}

	assert raster.dataset.closed


def test_mosaic_rejects_a_missing_quadrant(quadrants, tmp_path):
	with pytest.raises(ValueError, match='complete mosaic'):
		build_mosaic(quadrants[:-1], tmp_path / 'global.vrt')


@pytest.mark.django_db
def test_tiled_resolution_command_downloads_all_parts_and_loads_one_catalog(quadrants, tmp_path, settings, monkeypatch):
	settings.MEDIA_ROOT = tmp_path / 'media'
	settings.TERRAIN_ROOT = tmp_path / 'terrain'
	monkeypatch.setitem(PRESETS, '256', TerrainPreset(256, 0))
	filenames = global_source_filenames(256)
	requested_urls = []

	def download(source_url, directory, on_progress):
		requested_urls.append(source_url)
		directory.mkdir(parents=True, exist_ok=True)
		filename = source_url.rsplit('/', 1)[1].rsplit('.', 1)[0]

		return quadrants[filenames.index(filename)]

	monkeypatch.setattr('terrain.management.commands.ingest_terrain.download_file', download)
	output = StringIO()

	call_command('ingest_terrain', '256', stdout=output)

	dataset = TerrainDataset.objects.get(name='moon')
	assert dataset.tile_count == 6
	assert dataset.sources[0]['width'] == 8
	assert dataset.sources[0]['height'] == 4
	assert len(requested_urls) == 8
	assert all(f'{GLOBAL_SOURCE_URL}/{filename}.IMG' in requested_urls for filename in filenames)
	assert 'Loaded 6 tiles (256).' in output.getvalue()
	assert all(path.is_file() for path in quadrants)
	assert (settings.MEDIA_ROOT / 'sources/retained/LDEM_256.vrt').is_file()
	assert dataset.tiles.count() == 6
