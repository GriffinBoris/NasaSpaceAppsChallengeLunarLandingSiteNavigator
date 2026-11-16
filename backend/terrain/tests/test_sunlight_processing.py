import sqlite3
from concurrent.futures.process import BrokenProcessPool
from multiprocessing import active_children

import numpy
import pytest

from terrain.services.illumination_patch import patch_locations
from terrain.services.sunlight_processing import SunlightProcessor
from terrain.services.terrain_surface import TerrainSurface


@pytest.fixture
def sunlight_inputs(analysis_dataset):
	locations = patch_locations(12.345, 16.789, 2500, analysis_dataset.reference_radius, 3)
	locations = [location for location in locations if location is not None]
	surface = TerrainSurface(analysis_dataset)
	positions = [surface.surface_point(*location)[0] for location in locations]
	expected = numpy.array([[1.0, 0, 1, 0, 1], [0.0, 1, 0, 1, 0]])
	sun_vectors = numpy.empty((2, len(locations), 3))

	for frame_index in range(2):
		for point_index, position in enumerate(positions):
			direction = 1 if expected[frame_index, point_index] else -1
			sun_vectors[frame_index, point_index] = position / numpy.linalg.norm(position) * 149600000000 * direction

	return locations, sun_vectors, expected


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('build_horizons', [False, True])
@pytest.mark.parametrize('workers', [2, 4])
@pytest.mark.parametrize('body', ['SUN', 'EARTH'])
def test_spawned_workers_preserve_order_and_visibility(analysis_dataset, worker_database, sunlight_inputs, build_horizons, workers, body):
	locations, sun_vectors, expected = sunlight_inputs
	previous_children = {child.pid for child in active_children()}
	fractions = []
	prepared = []

	with SunlightProcessor(analysis_dataset.pk, locations, workers=workers, database=worker_database) as processor:
		for _, content in processor.prepare_profiles([None] * len(locations), build_missing=build_horizons):
			if content is not None:
				prepared.append(content)

		assert len({child.pid for child in active_children()} - previous_children) == workers

		for vectors in sun_vectors:
			for update in processor.calculate(vectors, 695700000.0 if body == 'SUN' else 6371000.0, body):
				completed, results = update

			assert completed == len(locations)
			field = 'visible_sun_fraction' if body == 'SUN' else 'visible_earth_fraction'
			fractions.append([result[field] for result in results])

			if body == 'EARTH':
				numpy.testing.assert_array_equal([result['earth_center_visible'] for result in results], expected[len(fractions) - 1])
			assert all(result['sampling_converged'] for result in results)

	numpy.testing.assert_array_equal(fractions, expected)
	assert len(prepared) == (len(locations) if build_horizons else 0)
	assert {child.pid for child in active_children()} <= previous_children

	with sqlite3.connect(worker_database['NAME']) as stored:
		for table in [
			'terrain_sunlighthorizon',
			'terrain_sunlightpreparation',
			'terrain_sunlightresult',
			'terrain_earthvisibilityresult',
			'terrain_sunlightstudy',
			'terrain_sunlightframe',
		]:
			assert stored.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == 0


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(('workers', 'repetitions'), [(8, 2), (16, 4)])
def test_higher_worker_counts_preserve_results_and_close_processes(analysis_dataset, worker_database, sunlight_inputs, workers, repetitions):
	locations, sun_vectors, expected = sunlight_inputs
	locations = locations * repetitions
	sun_vectors = numpy.tile(sun_vectors, (1, repetitions, 1))
	expected = numpy.tile(expected, (1, repetitions))
	previous_children = {child.pid for child in active_children()}
	actual = []

	with SunlightProcessor(analysis_dataset.pk, locations, workers=workers, database=worker_database) as processor:
		list(processor.prepare_profiles([None] * len(locations), build_missing=False))
		assert len({child.pid for child in active_children()} - previous_children) == workers

		for vectors in sun_vectors:
			for update in processor.calculate(vectors, 695700000.0):
				completed, results = update

			assert completed == len(locations)
			actual.append([result['visible_sun_fraction'] for result in results])

	numpy.testing.assert_array_equal(actual, expected)
	assert {child.pid for child in active_children()} <= previous_children


@pytest.mark.django_db(transaction=True)
def test_failed_worker_stops_other_workers_and_allows_retry(analysis_dataset, worker_database, sunlight_inputs):
	locations, sun_vectors, expected = sunlight_inputs
	previous_children = {child.pid for child in active_children()}
	contents = [b'invalid profile'] + [None] * (len(locations) - 1)

	with pytest.raises(OSError):
		with SunlightProcessor(analysis_dataset.pk, locations, workers=2, database=worker_database) as processor:
			list(processor.prepare_profiles(contents, build_missing=False))

	assert {child.pid for child in active_children()} <= previous_children

	with SunlightProcessor(analysis_dataset.pk, locations, workers=2, database=worker_database) as processor:
		list(processor.prepare_profiles([None] * len(locations), build_missing=False))

		for update in processor.calculate(sun_vectors[0], 695700000.0):
			completed, results = update

	numpy.testing.assert_array_equal([result['visible_sun_fraction'] for result in results], expected[0])
	assert {child.pid for child in active_children()} <= previous_children


@pytest.mark.django_db(transaction=True)
def test_interrupted_preparation_stops_workers_without_leaking_processes(analysis_dataset, worker_database, sunlight_inputs):
	locations, _, _ = sunlight_inputs
	previous_children = {child.pid for child in active_children()}

	with SunlightProcessor(analysis_dataset.pk, locations, workers=2, database=worker_database) as processor:
		preparation = processor.prepare_profiles([None] * len(locations), build_missing=True)

		for index, content in preparation:
			if index is not None:
				assert content is not None
				break

		preparation.close()

	assert {child.pid for child in active_children()} <= previous_children


@pytest.mark.django_db(transaction=True)
def test_failed_initialization_stops_started_workers(analysis_dataset, worker_database, sunlight_inputs):
	locations, _, _ = sunlight_inputs
	previous_children = {child.pid for child in active_children()}

	with pytest.raises(BrokenProcessPool):
		with SunlightProcessor(analysis_dataset.pk + 1, locations, workers=2, database=worker_database) as processor:
			list(processor.prepare_profiles([None] * len(locations), build_missing=False))

	assert {child.pid for child in active_children()} <= previous_children
