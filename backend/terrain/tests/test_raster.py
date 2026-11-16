import numpy
import rasterio
from rasterio.transform import from_bounds

from terrain.services.raster import TerrainRaster


def test_windowed_sampling_interpolates_across_blocks_and_the_dateline(tmp_path, monkeypatch):
	path = tmp_path / 'global.tif'
	heights = numpy.zeros((4, 1024), dtype=numpy.float32)
	heights[:, 511] = 100
	heights[:, 512] = 200
	heights[:, 0] = 300
	heights[:, -1] = 500

	with rasterio.open(
		path,
		'w',
		driver='GTiff',
		width=1024,
		height=4,
		count=1,
		dtype='float32',
		crs='+proj=longlat +R=1737400 +no_defs',
		transform=from_bounds(-180, -90, 180, 90, 1024, 4),
	) as dataset:
		dataset.write(heights, 1)

	original_open = rasterio.open
	opened_datasets = []
	read_windows = []

	class WindowedReader:
		def __init__(self, dataset):
			self.dataset = dataset

		def __getattr__(self, name):
			return getattr(self.dataset, name)

		def __enter__(self):
			return self

		def __exit__(self, exception_type, exception, traceback):
			self.dataset.close()

		def read(self, band, window, masked):
			read_windows.append(window)

			return self.dataset.read(band, window=window, masked=masked)

	def open_dataset(source_path):
		dataset = original_open(source_path)
		opened_datasets.append(dataset)

		return WindowedReader(dataset)

	monkeypatch.setattr('terrain.services.raster.rasterio.open', open_dataset)

	with TerrainRaster(path, '', is_global=True) as raster:
		longitudes = numpy.array([0.0, -180.0, 180.0])
		latitudes = numpy.zeros(3)

		numpy.testing.assert_array_equal(raster.sample(longitudes, latitudes), [150, 400, 400])

	assert all(window.width * window.height <= 512 * 512 for window in read_windows)
	assert all(dataset.closed for dataset in opened_datasets)


def test_worker_readers_reuse_metadata_without_rehashing_sources(global_source, monkeypatch):
	with TerrainRaster(global_source, 'https://example.com/global.tif', is_global=True) as raster:
		metadata = raster.metadata

	def reject_hashing(*args, **kwargs):
		raise AssertionError('Worker readers must not hash source files again.')

	monkeypatch.setattr('terrain.services.raster.hashlib.file_digest', reject_hashing)

	with TerrainRaster(global_source, metadata['url'], is_global=True, metadata=metadata) as raster:
		assert raster.metadata == metadata
		numpy.testing.assert_array_equal(raster.sample(numpy.array([0.0]), numpy.array([0.0])), [100])

	assert raster.dataset.closed
