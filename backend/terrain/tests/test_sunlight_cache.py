from datetime import UTC, datetime, timedelta
from io import StringIO
from threading import Event

import numpy
import pytest
from django.core.management import call_command

from terrain.models.SunlightHorizon import SunlightHorizon
from terrain.models.SunlightPreparation import SunlightPreparation
from terrain.models.SunlightResult import SunlightResult
from terrain.models.SunlightSelection import SunlightSelection
from terrain.models.TerrainDataset import TerrainDataset
from terrain.models.TerrainTile import TerrainTile
from terrain.services.sunlight_preparation import prepare_selection, restore_selection
from terrain.services.sunlight_result_cache import SunlightResultCache
from terrain.services.sunlight_samples import SunlightSamples

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('radius_meters', [None, 1250])
def test_prepared_samples_restore_exact_geometry_without_reading_terrain(analysis_dataset, monkeypatch, radius_meters):
	monkeypatch.setattr('terrain.services.illumination_patch.PATCH_GRID_SIZE', 3)
	selection = {'latitude': 12.345, 'longitude': 16.789, 'radius_meters': radius_meters}
	preparation = prepare_selection(analysis_dataset, selection)
	preparation.refresh_from_db()
	expected = [sample for sample in preparation.samples if sample is not None]

	def fail_read(*arguments):
		raise AssertionError('Prepared samples must not read terrain again.')

	monkeypatch.setattr('terrain.services.terrain_surface.TerrainSurface.surface_point', fail_read)
	stored = prepare_selection(analysis_dataset, {**selection, 'name': 'Renamed'})
	points, region = restore_selection(stored)
	locations = [(point.latitude, point.longitude) for point in points]
	worker_samples = SunlightSamples(analysis_dataset.pk, locations, Event(), geometry=expected)

	assert stored.pk == preparation.pk
	assert SunlightPreparation.objects.count() == 1
	assert (region is None) == (radius_meters is None)
	assert [point.geometry() for point in points] == expected
	assert [point.geometry() for point in worker_samples.points] == expected
	assert all(point.position.dtype == numpy.float64 and point.normal.dtype == numpy.float64 for point in points)


@pytest.mark.parametrize('changed_field,changed_value', [('latitude', 12.346), ('longitude', 16.790), ('radius_meters', 2500)])
def test_preparation_requires_matching_site_geometry(analysis_dataset, monkeypatch, changed_field, changed_value):
	monkeypatch.setattr('terrain.services.illumination_patch.PATCH_GRID_SIZE', 3)
	selection = {'latitude': 12.345, 'longitude': 16.789, 'radius_meters': 1250}
	first = prepare_selection(analysis_dataset, selection)

	second = prepare_selection(analysis_dataset, {**selection, changed_field: changed_value})

	assert first.pk != second.pk


def test_preparation_requires_matching_dataset_grid_and_version(analysis_dataset, monkeypatch):
	monkeypatch.setattr('terrain.services.illumination_patch.PATCH_GRID_SIZE', 3)
	selection = {'latitude': 12.345, 'longitude': 16.789, 'radius_meters': 1250}
	first = prepare_selection(analysis_dataset, selection)
	monkeypatch.setattr('terrain.services.illumination_patch.PATCH_GRID_SIZE', 5)
	new_grid = prepare_selection(analysis_dataset, selection)
	monkeypatch.setattr('terrain.services.sunlight_preparation.PREPARATION_VERSION', 2)
	new_version = prepare_selection(analysis_dataset, selection)
	other_dataset = TerrainDataset.objects.create(
		name='other',
		status='ready',
		storage_format='int16-delta-gzip',
		frame='MOON_ME_DE421',
		reference_radius=1737400,
		tile_size=33,
		max_level=0,
		tile_count=6,
		refinements=[],
		sources=[],
	)
	for tile in analysis_dataset.tiles.all():
		TerrainTile.objects.create(dataset=other_dataset, face=tile.face, level=tile.level, tile_x=tile.tile_x, tile_y=tile.tile_y, data=tile.data)

	new_dataset = prepare_selection(other_dataset, selection)

	assert len({first.pk, new_grid.pk, new_version.pk, new_dataset.pk}) == 4
	assert len(first.samples) == 9
	assert len(new_grid.samples) == 25


def test_shared_results_require_matching_time_ephemeris_and_calculation_version(analysis_dataset, monkeypatch):
	preparation = prepare_selection(analysis_dataset, {'latitude': 0, 'longitude': 0, 'radius_meters': None})
	start_time = datetime(2026, 11, 11, tzinfo=UTC)
	end_time = start_time + timedelta(minutes=15)
	cache = SunlightResultCache(preparation, 'a' * 64)
	result = cache.store(start_time, {'visible_sun_fraction': 0.75}, None)

	assert cache.result_ids(start_time, end_time) == {start_time: result.pk}
	assert cache.result_ids(start_time - timedelta(minutes=15), start_time) == {}
	assert cache.result_ids(end_time, end_time + timedelta(minutes=15)) == {}
	assert SunlightResultCache(preparation, 'b' * 64).result_ids(start_time, end_time) == {}
	monkeypatch.setattr('terrain.services.sunlight_result_cache.CALCULATION_VERSION', 2)
	assert SunlightResultCache(preparation, 'a' * 64).result_ids(start_time, end_time) == {}
	assert SunlightResult.objects.count() == 1


def test_prepare_command_stores_and_reuses_horizons_without_ephemeris_data(analysis_dataset, monkeypatch):
	selection = SunlightSelection.objects.create(name='Rim', latitude=12.345, longitude=16.789, radius_meters=None)
	output = StringIO()
	call_command('prepare_sunlight', analysis_dataset.pk, selection.pk, workers=1, stdout=output)
	assert SunlightPreparation.objects.count() == 1
	assert SunlightHorizon.objects.count() == 1
	assert not SunlightResult.objects.exists()
	assert '100%' in output.getvalue()

	def fail_build(*arguments):
		raise AssertionError('A completed preparation must be reused.')

	monkeypatch.setattr('terrain.services.terrain_surface.TerrainSurface.surface_point', fail_build)
	monkeypatch.setattr('terrain.services.horizon_builder.HorizonBuilder.build', fail_build)

	call_command('prepare_sunlight', analysis_dataset.pk, selection.pk, workers=1, stdout=output)

	assert SunlightPreparation.objects.count() == 1
	assert SunlightHorizon.objects.count() == 1
