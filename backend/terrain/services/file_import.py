import numpy

from terrain.models.TerrainDataset import TerrainDataset
from terrain.services.dataset_writer import TerrainDatasetWriter
from terrain.services.tile_encoding import encode_heights
from terrain.services.tile_reader import decode_tile_content, read_tile_content


def file_tile_coordinates(dataset):
	for face in range(6):
		yield face, 0, 0, 0

	for refinement in dataset.refinements:
		face, level, tile_x, tile_y = map(int, refinement.split('/'))

		for child_y in range(2):
			for child_x in range(2):
				yield face, level + 1, tile_x * 2 + child_x, tile_y * 2 + child_y


def import_file_tiles(source_dataset, on_progress):
	if source_dataset.status != TerrainDataset.Status.FILES:
		raise ValueError('This dataset already uses database tile rows.')

	dataset = TerrainDataset(
		name=source_dataset.name,
		status=TerrainDataset.Status.LOADING,
		storage_format=TerrainDataset.StorageFormat.INT16_DELTA_GZIP,
		frame=source_dataset.frame,
		reference_radius=source_dataset.reference_radius,
		tile_size=source_dataset.tile_size,
		max_level=source_dataset.max_level,
		tile_count=source_dataset.tile_count,
		refinements=source_dataset.refinements,
		sources=source_dataset.sources,
	)
	total_steps = source_dataset.tile_count + 1
	on_progress(0, total_steps)

	with TerrainDatasetWriter(dataset) as writer:
		for completed_tiles, coordinates in enumerate(file_tile_coordinates(source_dataset), start=1):
			content = read_tile_content(source_dataset, *coordinates)
			heights = decode_tile_content(content, source_dataset.storage_format)

			if heights.size != source_dataset.tile_size**2 or not numpy.isfinite(heights).all():
				raise ValueError('A tile contains missing heights or an unexpected number of samples.')

			if source_dataset.storage_format == TerrainDataset.StorageFormat.FLOAT32:
				content = encode_heights(heights)

			writer.add(*coordinates, content)
			on_progress(completed_tiles, total_steps)

		dataset = writer.publish()

	on_progress(total_steps, total_steps)

	return dataset
