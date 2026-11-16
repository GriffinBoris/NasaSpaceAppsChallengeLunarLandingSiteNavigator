import hashlib
from collections import OrderedDict
from pathlib import Path

import numpy
import rasterio
from rasterio.warp import transform
from rasterio.windows import Window

from terrain.services.tile_grid import REFERENCE_RADIUS

GEOGRAPHIC_CRS = f'+proj=longlat +R={REFERENCE_RADIUS} +no_defs'
BLOCK_SIZE = 512
CACHED_BLOCKS = 64


def source_files(dataset):
	filenames = set(dataset.files)

	if dataset.driver == 'VRT':
		for filename in dataset.files:
			if filename == dataset.name:
				continue

			with rasterio.open(filename) as source_dataset:
				filenames.update(source_dataset.files)

	return sorted(filenames)


def normalize_heights(values, scale, offset, driver):
	heights = values.astype(numpy.float32) * scale

	if driver == 'PDS':
		if offset != REFERENCE_RADIUS:
			raise ValueError('The PDS reference radius must be 1737400 meters.')

		return heights

	return heights + offset


def raster_metadata(dataset, source_url):
	files = []

	for filename in source_files(dataset):
		file_path = Path(filename)

		with file_path.open('rb') as source_file:
			checksum = hashlib.file_digest(source_file, 'sha256').hexdigest()

		files.append({'name': file_path.name, 'sha256': checksum})

	return {
		'filename': Path(dataset.name).name,
		'url': source_url,
		'files': files,
		'crs': dataset.crs.to_wkt(),
		'width': dataset.width,
		'height': dataset.height,
		'scale': dataset.scales[0],
		'offset': dataset.offsets[0],
	}


class TerrainRaster:
	def __init__(self, path, source_url, is_global, metadata=None):
		self.path = Path(path)

		with rasterio.open(path) as dataset:
			if dataset.crs is None:
				raise ValueError('The raster must have a lunar coordinate system.')

			projection = dataset.crs.to_dict()
			radius = projection.get('R', projection.get('a'))

			if radius != REFERENCE_RADIUS:
				raise ValueError('The raster must use the 1737400 meter lunar reference sphere.')

			self.crs = dataset.crs
			self.transform = dataset.transform
			self.is_global = is_global

			self.height = dataset.height
			self.width = dataset.width
			self.scale = dataset.scales[0]
			self.offset = dataset.offsets[0]
			self.driver = dataset.driver
			self.blocks = OrderedDict()

			if is_global:
				left, bottom, right, top = dataset.bounds
				inset = (right - left) * 0.000001
				longitudes, latitudes = transform(dataset.crs, GEOGRAPHIC_CRS, [left + inset, right - inset], [bottom, top])
				latitude_span = latitudes[1] - latitudes[0]
				longitude_span = (longitudes[1] - longitudes[0]) % 360

				if latitude_span < 179.9 or longitude_span < 359.9:
					raise ValueError('The base raster must cover all longitudes and both poles.')

			if metadata is None:
				self.metadata = raster_metadata(dataset, source_url)
			else:
				self.metadata = metadata

		self.dataset = rasterio.open(path)

		try:
			if self.is_global:
				self.north_pole_height = self._pole_height(0)
				self.south_pole_height = self._pole_height(self.height - 1)
		except Exception:
			self.close()
			raise

	def __enter__(self):
		return self

	def __exit__(self, exception_type, exception, traceback):
		self.close()

	def close(self):
		self.dataset.close()
		self.blocks.clear()

	def _pole_height(self, row):
		values = self.dataset.read(1, window=Window(0, row, self.width, 1), masked=True).astype(numpy.float32).filled(numpy.nan)
		heights = normalize_heights(values, self.scale, self.offset, self.driver)

		return numpy.nanmean(heights)

	def _read_pixels(self, rows, columns):
		block_column_count = (self.width + BLOCK_SIZE - 1) // BLOCK_SIZE
		block_identifiers = (rows // BLOCK_SIZE) * block_column_count + columns // BLOCK_SIZE
		heights = numpy.empty(rows.shape, dtype=numpy.float32)

		for block_identifier in numpy.unique(block_identifiers):
			block_row, block_column = divmod(int(block_identifier), block_column_count)
			block_key = (block_row, block_column)

			if block_key in self.blocks:
				block = self.blocks.pop(block_key)
			else:
				window = Window(block_column * BLOCK_SIZE, block_row * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
				values = self.dataset.read(1, window=window, masked=True).astype(numpy.float32).filled(numpy.nan)
				block = normalize_heights(values, self.scale, self.offset, self.driver)

			self.blocks[block_key] = block

			if len(self.blocks) > CACHED_BLOCKS:
				self.blocks.popitem(last=False)

			selection = block_identifiers == block_identifier
			local_rows = rows[selection] - block_row * BLOCK_SIZE
			local_columns = columns[selection] - block_column * BLOCK_SIZE
			heights[selection] = block[local_rows, local_columns]

		return heights

	def sample(self, longitudes, latitudes):
		shape = longitudes.shape
		sampled_heights = numpy.full(shape, numpy.nan, dtype=numpy.float32)
		sample_selection = numpy.ones(shape, dtype=bool)

		if not self.is_global:
			sample_selection = latitudes < -60

		if not sample_selection.any():
			return sampled_heights

		projected_x, projected_y = transform(GEOGRAPHIC_CRS, self.crs, longitudes[sample_selection].tolist(), latitudes[sample_selection].tolist())
		inverse_transform = ~self.transform
		columns, rows = inverse_transform @ (numpy.asarray(projected_x), numpy.asarray(projected_y))

		columns = columns - 0.5
		rows = rows - 0.5
		samples = self._sample_pixels(columns, rows)

		if self.is_global:
			selected_latitudes = latitudes[sample_selection]
			samples[selected_latitudes > 89.999999] = self.north_pole_height
			samples[selected_latitudes < -89.999999] = self.south_pole_height

		sampled_heights[sample_selection] = samples

		return sampled_heights

	def _sample_pixels(self, columns, rows):
		valid_samples = numpy.isfinite(columns) & numpy.isfinite(rows)

		if self.is_global:
			columns = columns % self.width
			rows = numpy.clip(rows, 0, self.height - 1)
		else:
			valid_samples &= (columns >= 0) & (columns <= self.width - 1)
			valid_samples &= (rows >= 0) & (rows <= self.height - 1)
			columns = numpy.clip(columns, 0, self.width - 1)
			rows = numpy.clip(rows, 0, self.height - 1)

		columns = numpy.where(valid_samples, columns, 0)
		rows = numpy.where(valid_samples, rows, 0)

		left_columns = numpy.floor(columns).astype(int)
		top_rows = numpy.floor(rows).astype(int)
		right_columns = numpy.minimum(left_columns + 1, self.width - 1)
		bottom_rows = numpy.minimum(top_rows + 1, self.height - 1)

		if self.is_global:
			right_columns = (left_columns + 1) % self.width

		horizontal_weight = columns - left_columns
		vertical_weight = rows - top_rows

		top_heights = (
			self._read_pixels(top_rows, left_columns) * (1 - horizontal_weight) + self._read_pixels(top_rows, right_columns) * horizontal_weight
		)
		bottom_heights = (
			self._read_pixels(bottom_rows, left_columns) * (1 - horizontal_weight) + self._read_pixels(bottom_rows, right_columns) * horizontal_weight
		)

		samples = top_heights * (1 - vertical_weight) + bottom_heights * vertical_weight

		samples[~valid_samples] = numpy.nan

		return samples
