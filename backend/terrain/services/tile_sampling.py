import numpy

from terrain.services.tile_encoding import encode_heights
from terrain.services.tile_grid import tile_coordinates


class TerrainTileSampler:
	def __init__(self, global_raster, south_pole_raster, tile_size):
		self.global_raster = global_raster
		self.south_pole_raster = south_pole_raster
		self.tile_size = tile_size

	def sample(self, coordinates):
		longitudes, latitudes = tile_coordinates(*coordinates, self.tile_size)
		heights = self.global_raster.sample(longitudes, latitudes)

		if self.south_pole_raster is not None and coordinates[0] == 3:
			detail_heights = self.south_pole_raster.sample(longitudes, latitudes)
			detail_coverage = numpy.isfinite(detail_heights)
			heights[detail_coverage] = detail_heights[detail_coverage]

		if not numpy.isfinite(heights).all():
			raise ValueError('The global source contains missing heights in the generated terrain.')

		return heights

	def encode_batch(self, tiles):
		results = []

		for coordinates in tiles:
			heights = self.sample(coordinates)
			content = encode_heights(heights)
			results.append((coordinates, content))

		return results
