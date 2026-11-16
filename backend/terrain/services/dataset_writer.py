from terrain.models.TerrainDataset import TerrainDataset
from terrain.models.TerrainTile import TerrainTile

WRITE_BATCH_SIZE = 1000


class TerrainDatasetWriter:
	def __init__(self, dataset):
		self.dataset = dataset
		self.pending_tiles = []
		self.tile_count = 0
		self.stored_bytes = 0

	def __enter__(self):
		self.dataset.save(force_insert=True)

		return self

	def __exit__(self, exception_type, exception, traceback):
		if exception_type is not None:
			self.dataset.delete()

	def add(self, face, level, tile_x, tile_y, content):
		self.pending_tiles.append(
			TerrainTile(dataset=self.dataset, face=face, level=level, tile_x=tile_x, tile_y=tile_y, data=content),
		)
		self.tile_count += 1
		self.stored_bytes += len(content)

		if len(self.pending_tiles) >= WRITE_BATCH_SIZE:
			self._flush()

	def _flush(self):
		TerrainTile.objects.bulk_create(self.pending_tiles, batch_size=WRITE_BATCH_SIZE)
		self.pending_tiles.clear()

	def publish(self):
		if self.tile_count != self.dataset.tile_count:
			raise ValueError('Stored tile count does not match the dataset plan.')

		self._flush()
		self.dataset.tile_count = self.tile_count
		self.dataset.status = TerrainDataset.Status.READY
		self.dataset.save(update_fields=['tile_count', 'status', 'updated_ts'])

		return self.dataset
