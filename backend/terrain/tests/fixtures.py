from datetime import UTC, datetime, timedelta

from terrain.models.SunlightPreparation import SunlightPreparation
from terrain.models.SunlightSelection import SunlightSelection
from terrain.models.SunlightStudy import SunlightStudy
from terrain.models.TerrainDataset import TerrainDataset


def create_terrain_dataset(tile_count=0):
	return TerrainDataset.objects.create(
		name='moon',
		status=TerrainDataset.Status.READY,
		storage_format=TerrainDataset.StorageFormat.INT16_DELTA_GZIP,
		frame='MOON_ME_DE421',
		reference_radius=1737400,
		tile_size=33,
		max_level=0,
		tile_count=tile_count,
		refinements=[],
		sources=[],
	)


def create_selection(name='Rim'):
	return SunlightSelection.objects.create(name=name, latitude=0, longitude=0, radius_meters=None)


def create_study(dataset, selection):
	start_time = datetime(2026, 11, 11, 12, tzinfo=UTC)

	return SunlightStudy.objects.create(
		name='Morning',
		dataset=dataset,
		selections=[
			{
				'id': selection.pk,
				'name': selection.name,
				'latitude': selection.latitude,
				'longitude': selection.longitude,
				'radius_meters': selection.radius_meters,
			}
		],
		start_time=start_time,
		end_time=start_time + timedelta(minutes=10),
		step_seconds=300,
		expected_frames=2,
	)


def create_preparation(dataset):
	return SunlightPreparation.objects.create(
		dataset=dataset,
		latitude=0,
		longitude=0,
		radius_meters=0,
		grid_size=1,
		version=1,
		samples=[{'latitude': 0, 'longitude': 0, 'position': [1737400, 0, 0], 'normal': [1, 0, 0], 'level': 0}],
	)
