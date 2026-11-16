import sqlite3
from contextlib import ExitStack
from types import SimpleNamespace

import numpy
import pytest
import rasterio
from django.db import connection
from rasterio.transform import from_bounds

from terrain.models.TerrainTile import TerrainTile
from terrain.services.raster import TerrainRaster
from terrain.services.surface_coordinates import cube_surface_directions, tile_bounds
from terrain.services.terrain_surface import TerrainSurface
from terrain.services.tile_encoding import encode_heights
from terrain.tests.fixtures import create_terrain_dataset


@pytest.fixture
def worker_database(analysis_dataset, tmp_path):
	path = tmp_path / 'terrain.sqlite3'

	with sqlite3.connect(path) as destination:
		connection.connection.backup(destination)

	return dict(connection.settings_dict, NAME=str(path))


@pytest.fixture
def rough_surface(monkeypatch):
	refinements = []

	for face in range(6):
		for level in range(2):
			for tile_y in range(2**level):
				for tile_x in range(2**level):
					refinements.append(f'{face}/{level}/{tile_x}/{tile_y}')

	dataset = SimpleNamespace(
		status='ready', storage_format='int16-delta-gzip', frame='MOON_ME_DE421', reference_radius=1737400, tile_size=9, refinements=refinements
	)

	def heights(dataset, face, level, tile_x, tile_y):
		left, right, top, bottom = tile_bounds(level, tile_x, tile_y)
		horizontal, vertical = numpy.meshgrid(numpy.linspace(left, right, 9), numpy.linspace(top, bottom, 9))
		directions = cube_surface_directions(face, horizontal, vertical)
		values = 1000 * (numpy.sin(directions[:, :, 0] * 17) + numpy.cos(directions[:, :, 1] * 13))

		return values.ravel()

	monkeypatch.setattr('terrain.services.terrain_surface.read_tile_heights', heights)

	return TerrainSurface(dataset)


@pytest.fixture
def analysis_dataset():
	dataset = create_terrain_dataset(tile_count=6)
	content = encode_heights(numpy.zeros((33, 33)))

	for face in range(6):
		TerrainTile.objects.create(dataset=dataset, face=face, level=0, tile_x=0, tile_y=0, data=content)

	return dataset


@pytest.fixture
def global_source(tmp_path):
	path = tmp_path / 'global.tif'

	with rasterio.open(
		path,
		'w',
		driver='GTiff',
		width=8,
		height=4,
		count=1,
		dtype='float32',
		crs='+proj=longlat +R=1737400 +no_defs',
		transform=from_bounds(-180, -90, 180, 90, 8, 4),
	) as dataset:
		dataset.write(numpy.full((4, 8), 100, dtype=numpy.float32), 1)

	return path


@pytest.fixture
def open_raster():
	with ExitStack() as resources:

		def open_source(source_path, source_url, is_global):
			return resources.enter_context(TerrainRaster(source_path, source_url, is_global))

		yield open_source


@pytest.fixture
def south_pole_source(tmp_path):
	path = tmp_path / 'south.tif'

	with rasterio.open(
		path,
		'w',
		driver='GTiff',
		width=8,
		height=8,
		count=1,
		dtype='float32',
		crs='+proj=stere +lat_0=-90 +lon_0=0 +k=1 +R=1737400 +units=m +no_defs',
		transform=from_bounds(-100000, -100000, 100000, 100000, 8, 8),
	) as dataset:
		dataset.write(numpy.full((8, 8), 800, dtype=numpy.float32), 1)

	return path
