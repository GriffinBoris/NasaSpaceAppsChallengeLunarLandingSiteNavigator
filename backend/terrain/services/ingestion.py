import uuid

import numpy
from core.lunar import LUNAR_FRAME

from terrain.models.TerrainDataset import TerrainDataset
from terrain.services.dataset_writer import TerrainDatasetWriter
from terrain.services.tile_grid import REFERENCE_RADIUS, tile_coordinates
from terrain.services.tile_processing import TerrainTileProcessor


class TerrainIngestion:
	def __init__(self, global_raster, south_pole_raster=None, global_level=4, detail_level=8, tile_size=65):
		self.global_raster = global_raster
		self.south_pole_raster = south_pole_raster

		self.global_level = global_level
		self.detail_level = detail_level if south_pole_raster is not None else global_level
		self.tile_size = tile_size

		self.storage_key = uuid.uuid4()

		self.refinements = []
		self.stored_bytes = 0

	def run(self, name, on_progress=None, workers=2):
		planned_tiles = []

		for face in range(6):
			self._plan_tiles(planned_tiles, face, 0, 0, 0)

		total_steps = len(planned_tiles) + 1
		sources = [self.global_raster.metadata]

		if self.south_pole_raster is not None:
			sources.append(self.south_pole_raster.metadata)

		dataset = TerrainDataset(
			name=name,
			status=TerrainDataset.Status.LOADING,
			storage_key=self.storage_key,
			storage_format=TerrainDataset.StorageFormat.INT16_DELTA_GZIP,
			frame=LUNAR_FRAME,
			reference_radius=REFERENCE_RADIUS,
			tile_size=self.tile_size,
			max_level=self.detail_level,
			tile_count=len(planned_tiles),
			refinements=self.refinements,
			sources=sources,
		)

		with (
			TerrainTileProcessor(self.global_raster, self.south_pole_raster, self.tile_size, workers) as processor,
			TerrainDatasetWriter(dataset) as writer,
		):
			if on_progress is not None:
				on_progress(0, total_steps)

			completed_tiles = 0

			for batch in processor.process(planned_tiles):
				for coordinates, content in batch:
					writer.add(*coordinates, content)
					completed_tiles += 1

					if on_progress is not None:
						on_progress(completed_tiles, total_steps)

			dataset = writer.publish()

		self.stored_bytes = writer.stored_bytes

		if on_progress is not None:
			on_progress(total_steps, total_steps)

		return dataset

	def _plan_tiles(self, planned_tiles, face, level, tile_x, tile_y):
		planned_tiles.append((face, level, tile_x, tile_y))

		should_refine = level < self.global_level

		if not should_refine and face == 3 and self.south_pole_raster is not None and level < self.detail_level:
			longitudes, latitudes = tile_coordinates(face, level, tile_x, tile_y, self.tile_size)
			detail_heights = self.south_pole_raster.sample(longitudes, latitudes)
			should_refine = numpy.isfinite(detail_heights).any()

		if not should_refine:
			return

		self.refinements.append(f'{face}/{level}/{tile_x}/{tile_y}')

		for child_y in range(2):
			for child_x in range(2):
				self._plan_tiles(planned_tiles, face, level + 1, tile_x * 2 + child_x, tile_y * 2 + child_y)
