import os
from concurrent.futures import Future
from concurrent.futures.process import BrokenProcessPool
from contextlib import ExitStack
from multiprocessing import active_children

import numpy
import pytest
import rasterio

from terrain.models.TerrainTile import TerrainTile
from terrain.services.ingestion import TerrainIngestion
from terrain.services.raster import TerrainRaster
from terrain.services.tile_processing import TerrainTileProcessor
from terrain.services.tile_sampling import TerrainTileSampler


def tile_coordinates():
	for face in range(6):
		for row in range(16):
			for column in range(16):
				yield face, 4, column, row


@pytest.mark.parametrize('workers', [2, 4, 8])
@pytest.mark.parametrize('include_south_pole', [False, True])
def test_parallel_batches_match_serial_sampling_and_release_worker_processes(global_source, south_pole_source, workers, include_south_pole):
	with rasterio.open(global_source, 'r+') as source:
		heights = numpy.arange(32, dtype=numpy.float32).reshape(4, 8) * 25 - 400
		source.write(heights, 1)

	coordinates = list(tile_coordinates())
	previous_children = {process.pid for process in active_children()}

	with ExitStack() as resources:
		raster = resources.enter_context(TerrainRaster(global_source, '', is_global=True))
		south_pole_raster = None

		if include_south_pole:
			south_pole_raster = resources.enter_context(TerrainRaster(south_pole_source, '', is_global=False))

		sampler = TerrainTileSampler(raster, south_pole_raster, 5)
		expected = dict(sampler.encode_batch(coordinates))

		with TerrainTileProcessor(raster, south_pole_raster, 5, workers) as processor:
			results = []

			for batch in processor.process(coordinates):
				results.extend(batch)

	assert len(results) == len(coordinates)
	assert dict(results) == expected
	assert {process.pid for process in active_children()} == previous_children


def test_worker_sampling_failure_releases_workers(global_source):
	with rasterio.open(global_source, 'r+') as source:
		heights = numpy.full((4, 8), 100, dtype=numpy.float32)
		heights[1, 3] = numpy.nan
		source.write(heights, 1)

	previous_children = {process.pid for process in active_children()}
	coordinates = [(face, 0, 0, 0) for face in range(6)]

	with TerrainRaster(global_source, '', is_global=True) as raster:
		with pytest.raises(ValueError, match='missing heights'):
			with TerrainTileProcessor(raster, None, 5, 2) as processor:
				list(processor.process(coordinates))

	assert {process.pid for process in active_children()} == previous_children


def test_worker_initialization_failure_does_not_leave_child_processes(global_source):
	previous_children = {process.pid for process in active_children()}

	with TerrainRaster(global_source, '', is_global=True) as raster:
		raster.path = global_source.with_name('missing.tif')

		with pytest.raises(BrokenProcessPool):
			with TerrainTileProcessor(raster, None, 5, 2) as processor:
				list(processor.process([(0, 0, 0, 0)]))

	assert {process.pid for process in active_children()} == previous_children


def test_processor_bounds_submitted_batches_and_cancels_remaining_work(global_source, monkeypatch):
	submitted_batches = []
	shutdown_calls = []

	class Executor:
		def __init__(self, max_workers, mp_context, initializer, initargs):
			assert max_workers == 2
			assert mp_context.get_start_method() == 'spawn'

		def submit(self, function, batch):
			submitted_batches.append(batch)
			future = Future()
			future.set_result(batch)

			return future

		def shutdown(self, wait, cancel_futures):
			shutdown_calls.append((wait, cancel_futures))

	monkeypatch.setattr('terrain.services.tile_processing.ProcessPoolExecutor', Executor)
	coordinates = list(tile_coordinates()) * 4

	with TerrainRaster(global_source, '', is_global=True) as raster:
		with TerrainTileProcessor(raster, None, 5, 2) as processor:
			results = processor.process(coordinates)
			first_batch = next(results)

			assert len(submitted_batches) == 4
			assert len(first_batch) == 64

	assert shutdown_calls == [(True, True)]
	assert len(submitted_batches) == 4


@pytest.mark.django_db(transaction=True)
def test_only_the_parent_writes_complete_thousand_row_groups_and_the_final_remainder(global_source, monkeypatch):
	original_bulk_create = TerrainTile.objects.bulk_create
	write_groups = []

	def bulk_create(tiles, batch_size):
		write_groups.append((os.getpid(), len(tiles), batch_size))

		return original_bulk_create(tiles, batch_size=batch_size)

	monkeypatch.setattr(TerrainTile.objects, 'bulk_create', bulk_create)

	with TerrainRaster(global_source, '', is_global=True) as raster:
		dataset = TerrainIngestion(raster, global_level=4, tile_size=5).run('moon', workers=2)

	assert write_groups == [(os.getpid(), 1000, 1000), (os.getpid(), 1000, 1000), (os.getpid(), 46, 1000)]
	assert dataset.tiles.count() == 2046
	assert dataset.status == dataset.Status.READY
