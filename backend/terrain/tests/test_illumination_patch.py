import json
from datetime import UTC, datetime

import numpy
import pytest
from django.urls import reverse

from terrain.models.TerrainDataset import TerrainDataset
from terrain.services.illumination_patch import PATCH_GRID_SIZE, patch_locations
from terrain.services.surface_coordinates import surface_direction
from terrain.services.terrain_surface import TerrainAnalysisUnavailable


@pytest.mark.parametrize('radius_meters', [250, 1250, 50000])
@pytest.mark.parametrize(('latitude', 'longitude'), [(0, 179.99), (89.999, 0), (90, 180), (-90, -179.99)])
def test_patch_grid_preserves_distances_at_the_poles_and_longitude_seam(latitude, longitude, radius_meters):
	locations = patch_locations(latitude, longitude, radius_meters, 1737400)
	center = surface_direction(latitude, longitude)

	assert len(locations) == PATCH_GRID_SIZE**2
	assert locations[len(locations) // 2] == pytest.approx((latitude, longitude), abs=1e-10)
	selected_locations = [location for location in locations if location is not None]

	assert all(-90 <= point_latitude <= 90 and -180 <= point_longitude <= 180 for point_latitude, point_longitude in selected_locations)

	assert len(selected_locations) < len(locations)

	for location in selected_locations:
		direction = surface_direction(*location)
		distance = numpy.arctan2(numpy.linalg.norm(numpy.cross(center, direction)), center @ direction) * 1737400

		assert distance <= radius_meters + 1e-6

	for index in (PATCH_GRID_SIZE // 2, len(locations) // 2 - PATCH_GRID_SIZE // 2):
		direction = surface_direction(*locations[index])
		distance = numpy.arctan2(numpy.linalg.norm(numpy.cross(center, direction)), center @ direction) * 1737400

		assert distance == pytest.approx(radius_meters, abs=1e-6)


@pytest.mark.django_db
@pytest.mark.parametrize(('sun_vector', 'expected_fraction'), [([149600000000.0, 0, 0], 1), ([-149600000000.0, 0, 0], 0)])
def test_public_patch_returns_computed_visibility_on_stored_terrain(client, analysis_dataset, monkeypatch, sun_vector, expected_fraction):
	monkeypatch.setattr('terrain.services.illumination_patch.PATCH_GRID_SIZE', 3)

	def surface_suns(timestamp, positions):
		assert timestamp == datetime(2026, 11, 11, 12, tzinfo=UTC)
		assert len(positions) == 5

		return [numpy.array(sun_vector) for position in positions], 695700000.0

	monkeypatch.setattr('terrain.services.illumination_patch.calculate_surface_suns', surface_suns)
	monkeypatch.setattr('terrain.services.illumination.calculate_surface_sun', lambda timestamp, position: (numpy.array(sun_vector), 695700000.0))
	url = reverse('terrain:illumination:terrain-illumination-patch-detail', kwargs={'dataset_id': analysis_dataset.id})
	response = client.get(
		url, {'timestamp': '2026-11-11T07:00:00-05:00', 'latitude': 0, 'longitude': 0}, HTTP_ACCEPT='application/x-ndjson, application/json'
	)

	assert response.status_code == 200
	assert response['Content-Type'] == 'application/x-ndjson'
	assert response['Cache-Control'] == 'no-store'

	events = [json.loads(line) for line in response.streaming_content]
	progress = [event['progress'] for event in events if event['type'] == 'progress']
	result = events[-1]['result']

	assert progress[0]['percentage'] == 0
	assert progress[-1] == {'completed': 6, 'total': 6, 'percentage': 100, 'stage': 'Complete'}
	assert [update['percentage'] for update in progress] == sorted(update['percentage'] for update in progress)
	assert set(result) == {'center', 'grid_size', 'radius_meters', 'spacing_meters', 'points'}
	assert result['center']['dataset_id'] == analysis_dataset.id
	assert result['center']['timestamp'] == '2026-11-11T12:00:00Z'
	assert result['center']['visible_sun_fraction'] == expected_fraction
	assert result['grid_size'] == 3
	assert result['radius_meters'] == 5000
	assert result['spacing_meters'] == 5000
	assert len(result['points']) == 9
	assert [index for index, point in enumerate(result['points']) if point is None] == [0, 2, 6, 8]

	for point in result['points']:
		if point is None:
			continue

		assert set(point) == {'visible_sun_fraction', 'sampling_converged'}
		assert point['visible_sun_fraction'] == expected_fraction
		assert point['sampling_converged'] is True


@pytest.mark.django_db
def test_patch_rejects_invalid_coordinates_and_unpublished_datasets(client, analysis_dataset):
	url = reverse('terrain:illumination:terrain-illumination-patch-detail', kwargs={'dataset_id': analysis_dataset.id})
	parameters = {'timestamp': '2026-11-11T12:00:00Z', 'latitude': 91, 'longitude': 0}

	response = client.get(url, parameters)

	assert response.status_code == 400
	assert response.data['errors'][0]['attr'] == 'latitude'

	analysis_dataset.status = TerrainDataset.Status.LOADING
	analysis_dataset.save(update_fields=['status'])
	parameters['latitude'] = 0

	assert client.get(url, parameters).status_code == 404


@pytest.mark.django_db
def test_patch_has_no_write_action(client, analysis_dataset):
	url = reverse('terrain:illumination:terrain-illumination-patch-detail', kwargs={'dataset_id': analysis_dataset.id})

	assert client.post(url, {}).status_code == 405


@pytest.mark.django_db
@pytest.mark.parametrize('radius_meters', [0, 249, 50001, 'invalid'])
def test_patch_rejects_invalid_radius_before_streaming(client, analysis_dataset, radius_meters):
	url = reverse('terrain:illumination:terrain-illumination-patch-detail', kwargs={'dataset_id': analysis_dataset.id})
	response = client.get(url, {'timestamp': '2026-11-11T12:00:00Z', 'latitude': 0, 'longitude': 0, 'radius_meters': radius_meters})

	assert response.status_code == 400
	assert response.data['errors'][0]['attr'] == 'radius_meters'


@pytest.mark.django_db
def test_closing_stream_stops_work_and_closes_calculation(client, analysis_dataset, monkeypatch):
	stages = []

	def calculation(dataset, **parameters):
		assert parameters['radius_meters'] == 1250

		try:
			yield {'type': 'progress', 'progress': {'completed': 0, 'total': 1, 'percentage': 0, 'stage': 'Preparing terrain'}}
			stages.append('calculated')
		finally:
			stages.append('closed')

	monkeypatch.setattr('terrain.views.illumination.views.IlluminationPatchView.calculation', staticmethod(calculation))
	url = reverse('terrain:illumination:terrain-illumination-patch-detail', kwargs={'dataset_id': analysis_dataset.id})
	response = client.get(url, {'timestamp': '2026-11-11T12:00:00Z', 'latitude': 0, 'longitude': 0, 'radius_meters': 1250})
	stream = iter(response.streaming_content)

	assert json.loads(next(stream))['progress']['percentage'] == 0
	assert stages == []

	response.close()

	assert stages == ['closed']


@pytest.mark.django_db
@pytest.mark.parametrize('expected', [True, False])
def test_stream_reports_calculation_failure_and_closes(client, analysis_dataset, monkeypatch, caplog, expected):
	closed = []

	def calculation(dataset, **parameters):
		try:
			yield {'type': 'progress', 'progress': {'completed': 0, 'total': 1, 'percentage': 0, 'stage': 'Preparing terrain'}}

			if expected:
				raise TerrainAnalysisUnavailable('Terrain is incomplete.')

			raise RuntimeError('internal details')
		finally:
			closed.append(True)

	monkeypatch.setattr('terrain.views.illumination.views.IlluminationPatchView.calculation', staticmethod(calculation))
	url = reverse('terrain:illumination:terrain-illumination-patch-detail', kwargs={'dataset_id': analysis_dataset.id})
	response = client.get(url, {'timestamp': '2026-11-11T12:00:00Z', 'latitude': 0, 'longitude': 0})
	events = [json.loads(line) for line in response.streaming_content]

	assert [event['type'] for event in events] == ['progress', 'error']
	assert events[-1]['message'] == ('Terrain is incomplete.' if expected else 'Unable to calculate visibility. Please try again.')
	assert closed == [True]
	assert caplog.records[-1].exc_info is not None
