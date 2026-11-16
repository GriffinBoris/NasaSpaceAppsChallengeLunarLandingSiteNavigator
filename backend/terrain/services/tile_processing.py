import atexit
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from contextlib import ExitStack
from itertools import batched, islice
from multiprocessing import get_context

from terrain.services.raster import TerrainRaster
from terrain.services.tile_sampling import TerrainTileSampler

worker_sampler: TerrainTileSampler


def initialize_tile_worker(global_source, south_pole_source, tile_size):
	global worker_sampler

	resources = ExitStack()

	try:
		path, metadata = global_source
		global_raster = resources.enter_context(TerrainRaster(path, metadata['url'], is_global=True, metadata=metadata))
		south_pole_raster = None

		if south_pole_source is not None:
			path, metadata = south_pole_source
			south_pole_raster = resources.enter_context(TerrainRaster(path, metadata['url'], is_global=False, metadata=metadata))

		worker_sampler = TerrainTileSampler(global_raster, south_pole_raster, tile_size)
		atexit.register(resources.close)
	except BaseException:
		resources.close()
		raise


def process_tile_batch(tiles):
	return worker_sampler.encode_batch(tiles)


class TerrainTileProcessor:
	def __init__(self, global_raster, south_pole_raster, tile_size, workers):
		self.global_source = (global_raster.path, global_raster.metadata)
		self.south_pole_source = None
		self.tile_size = tile_size
		self.workers = workers

		if south_pole_raster is not None:
			self.south_pole_source = (south_pole_raster.path, south_pole_raster.metadata)

	def __enter__(self):
		self.executor = ProcessPoolExecutor(
			max_workers=self.workers,
			mp_context=get_context('spawn'),
			initializer=initialize_tile_worker,
			initargs=(self.global_source, self.south_pole_source, self.tile_size),
		)

		return self

	def __exit__(self, exception_type, exception, traceback):
		self.executor.shutdown(wait=True, cancel_futures=True)

	def process(self, tiles):
		batches = iter(batched(tiles, 64))
		pending = set()

		for batch in islice(batches, self.workers * 2):
			pending.add(self.executor.submit(process_tile_batch, batch))

		while pending:
			completed, pending = wait(pending, return_when=FIRST_COMPLETED)

			while completed:
				future = completed.pop()
				yield future.result()

				batch = next(batches, None)

				if batch is not None:
					pending.add(self.executor.submit(process_tile_batch, batch))
