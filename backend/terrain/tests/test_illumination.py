from datetime import UTC, datetime

import numpy
import pytest
from core.tests.assertions import assert_validation_error
from django.urls import reverse
from ephemeris.services.positions import EphemerisTimeError, EphemerisUnavailable

from terrain.models.TerrainDataset import TerrainDataset
from terrain.services.illumination import calculate_illumination
from terrain.services.terrain_surface import TerrainAnalysisUnavailable, TerrainSurface

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(('sun_vector', 'expected_fraction'), [([149600000000.0, 0, 0], 1), ([-149600000000.0, 0, 0], 0)])
def test_stored_terrain_returns_day_and_night_without_source_files(analysis_dataset, monkeypatch, sun_vector, expected_fraction):
	monkeypatch.setattr('terrain.services.illumination.calculate_surface_sun', lambda timestamp, position: (numpy.array(sun_vector), 695700000.0))

	result = calculate_illumination(analysis_dataset, datetime(2026, 11, 11, tzinfo=UTC), 0, 0)

	assert result['visible_sun_fraction'] == expected_fraction
	assert result['analysis_level'] == 0
	assert result['dataset_id'] == analysis_dataset.id
	assert result['sampling_converged'] is True
	assert result['disk_sample_count'] == 1024
	assert result['sun_angular_radius_degrees'] == pytest.approx(0.2664493, abs=1e-6)


def test_sunrise_reports_partial_illumination(analysis_dataset, monkeypatch):
	position, normal, level = TerrainSurface(analysis_dataset).surface_point(0.5, 3)
	direction = numpy.cross(normal, numpy.array([0, 1, 0]))
	direction /= numpy.linalg.norm(direction)
	monkeypatch.setattr('terrain.services.illumination.calculate_surface_sun', lambda timestamp, position: (direction * 149600000000, 695700000.0))

	result = calculate_illumination(analysis_dataset, datetime(2026, 11, 11, tzinfo=UTC), 0.5, 3)

	assert result['visible_sun_fraction'] == pytest.approx(0.5, abs=0.005)


def test_unsupported_storage_does_not_return_a_guessed_result(analysis_dataset):
	analysis_dataset.storage_format = TerrainDataset.StorageFormat.FLOAT32

	with pytest.raises(TerrainAnalysisUnavailable, match='Int16'):
		calculate_illumination(analysis_dataset, datetime(2026, 11, 11, tzinfo=UTC), 0, 0)


def test_public_analysis_is_pinned_to_the_requested_dataset_and_utc_time(client, analysis_dataset, monkeypatch):
	TerrainDataset.objects.create(
		name='moon',
		status=TerrainDataset.Status.READY,
		frame='MOON_ME_DE421',
		reference_radius=1737400,
		tile_size=33,
		max_level=0,
		tile_count=0,
		refinements=[],
		sources=[],
	)
	monkeypatch.setattr(
		'terrain.services.illumination.calculate_surface_sun', lambda timestamp, position: (numpy.array([149600000000.0, 0, 0]), 695700000.0)
	)
	url = reverse('terrain:illumination:terrain-illumination-detail', kwargs={'dataset_id': analysis_dataset.id})

	response = client.get(url, {'timestamp': '2026-11-11T07:00:00-05:00', 'latitude': 0, 'longitude': 0})

	assert response.status_code == 200
	assert response.data == {
		'dataset_id': analysis_dataset.id,
		'timestamp': '2026-11-11T12:00:00Z',
		'latitude': 0.0,
		'longitude': 0.0,
		'frame': 'MOON_ME_DE421',
		'elevation_meters': pytest.approx(0, abs=1e-6),
		'analysis_level': 0,
		'sun_elevation_degrees': 90.0,
		'sun_azimuth_degrees': 0.0,
		'sun_angular_radius_degrees': pytest.approx(0.2664493, abs=1e-6),
		'visible_sun_fraction': 1.0,
		'disk_sample_count': 1024,
		'sampling_converged': True,
		'fraction_tolerance': 0.005,
	}


@pytest.mark.parametrize(
	('field', 'value'),
	[('timestamp', 'invalid'), ('latitude', 91), ('latitude', 'NaN'), ('longitude', 181), ('longitude', 'Infinity')],
)
def test_invalid_analysis_inputs_return_field_errors(client, analysis_dataset, field, value):
	parameters = {'timestamp': '2026-11-11T12:00:00Z', 'latitude': 0, 'longitude': 0}
	parameters[field] = value
	url = reverse('terrain:illumination:terrain-illumination-detail', kwargs={'dataset_id': analysis_dataset.id})

	response = client.get(url, parameters)

	assert response.status_code == 400
	assert response.data['errors'][0]['attr'] == field


@pytest.mark.parametrize('field', ['timestamp', 'latitude', 'longitude'])
def test_analysis_requires_time_and_coordinates(client, analysis_dataset, field):
	parameters = {'timestamp': '2026-11-11T12:00:00Z', 'latitude': 0, 'longitude': 0}
	del parameters[field]
	url = reverse('terrain:illumination:terrain-illumination-detail', kwargs={'dataset_id': analysis_dataset.id})

	response = client.get(url, parameters)

	assert response.status_code == 400
	assert response.data['errors'][0]['attr'] == field


def test_loading_datasets_cannot_be_analyzed(client, analysis_dataset):
	analysis_dataset.status = TerrainDataset.Status.LOADING
	analysis_dataset.save(update_fields=['status'])
	url = reverse('terrain:illumination:terrain-illumination-detail', kwargs={'dataset_id': analysis_dataset.id})

	assert client.get(url, {'timestamp': '2026-11-11T12:00:00Z', 'latitude': 0, 'longitude': 0}).status_code == 404


@pytest.mark.parametrize(
	('error', 'expected_status'),
	[(EphemerisUnavailable('Missing kernels'), 503), (EphemerisTimeError('Time is outside coverage'), 400)],
)
def test_ephemeris_failures_are_reported_without_an_illumination_result(client, analysis_dataset, monkeypatch, error, expected_status):
	client.raise_request_exception = False

	def fail_sun(timestamp, position):
		raise error

	monkeypatch.setattr('terrain.services.illumination.calculate_surface_sun', fail_sun)
	url = reverse('terrain:illumination:terrain-illumination-detail', kwargs={'dataset_id': analysis_dataset.id})

	response = client.get(url, {'timestamp': '2026-11-11T12:00:00Z', 'latitude': 0, 'longitude': 0})

	assert response.status_code == expected_status
	assert 'visible_sun_fraction' not in response.data

	if expected_status == 400:
		assert_validation_error(response, 'timestamp', 'invalid')


def test_analysis_has_no_write_action(client, analysis_dataset):
	url = reverse('terrain:illumination:terrain-illumination-detail', kwargs={'dataset_id': analysis_dataset.id})

	assert client.post(url, {}).status_code == 405


def test_unstable_sampling_is_reported_instead_of_claiming_convergence(analysis_dataset, monkeypatch):
	monkeypatch.setattr(
		'terrain.services.illumination.calculate_surface_sun', lambda timestamp, position: (numpy.array([149600000000.0, 0, 0]), 695700000.0)
	)
	blocked_fractions = iter((0.25, 0.75, 0.25))

	def blocked_rays(surface, origin, directions):
		return numpy.arange(len(directions)) < len(directions) * next(blocked_fractions)

	monkeypatch.setattr(TerrainSurface, 'blocked_rays', blocked_rays)

	result = calculate_illumination(analysis_dataset, datetime(2026, 11, 11, tzinfo=UTC), 0, 0)

	assert result['disk_sample_count'] == 4096
	assert result['sampling_converged'] is False
	assert result['visible_sun_fraction'] == 0.75
