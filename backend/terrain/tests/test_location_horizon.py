from datetime import UTC, datetime

import numpy
import pytest
from core.tests.assertions import assert_validation_error
from django.urls import reverse
from ephemeris.services.positions import EphemerisTimeError, EphemerisUnavailable

from terrain.models.SunlightHorizon import SunlightHorizon
from terrain.models.TerrainDataset import TerrainDataset
from terrain.services.horizon_profile import HORIZON_BIN_COUNT, HORIZON_VERSION, HorizonProfile

pytestmark = pytest.mark.django_db


@pytest.fixture
def horizon_inputs(analysis_dataset, monkeypatch):
	observations = []

	def body_vectors(times, position):
		observations.append((times, position))

		return {'SUN': [numpy.array([0.0, 1.5e11, 0])], 'EARTH': [numpy.array([0.0, 0, 3.8e8])]}

	monkeypatch.setattr('terrain.services.surface_directions.calculate_surface_body_series', body_vectors)
	url = reverse('terrain:horizon:location-horizon-detail', kwargs={'dataset_id': analysis_dataset.pk})

	return url, {'latitude': 0, 'longitude': 0, 'timestamp': '2026-11-11T12:00:00Z'}, observations


def test_location_horizon_shows_cached_terrain_and_surface_observer_directions(client, analysis_dataset, horizon_inputs):
	url, parameters, observations = horizon_inputs
	profile = HorizonProfile(numpy.full(HORIZON_BIN_COUNT, numpy.radians(1)), numpy.full(HORIZON_BIN_COUNT, numpy.radians(2)))
	SunlightHorizon.objects.create(dataset=analysis_dataset, latitude=0, longitude=0, version=HORIZON_VERSION, data=profile.encode())

	response = client.get(url, parameters)

	assert response.status_code == 200
	assert set(response.data) == {'dataset_id', 'latitude', 'longitude', 'timestamp', 'azimuth_offset_degrees', 'bounds', 'sun', 'earth'}
	assert response.data['dataset_id'] == analysis_dataset.pk
	assert response.data['timestamp'] == parameters['timestamp']
	assert response.data['sun'] == {'elevation_degrees': 0, 'azimuth_degrees': 90}
	assert response.data['earth'] == {'elevation_degrees': 0, 'azimuth_degrees': 0}
	assert response.data['bounds']['lower_elevation_degrees'] == pytest.approx([1] * 512)
	assert response.data['bounds']['upper_elevation_degrees'] == pytest.approx([2] * 512)
	assert observations[0][0] == [datetime(2026, 11, 11, 12, tzinfo=UTC)]
	assert numpy.linalg.norm(observations[0][1]) == pytest.approx(analysis_dataset.reference_radius, abs=1)
	assert SunlightHorizon.objects.count() == 1


def test_location_horizon_does_not_prepare_missing_profiles(client, horizon_inputs):
	url, parameters, _ = horizon_inputs

	response = client.get(url, parameters)

	assert response.status_code == 200
	assert response.data['bounds'] is None
	assert response.data['sun']['azimuth_degrees'] == 90
	assert not SunlightHorizon.objects.exists()


@pytest.mark.parametrize(
	('field', 'value', 'expected_code'),
	[('latitude', 91, 'max_value'), ('longitude', 181, 'max_value'), ('latitude', 'NaN', 'invalid'), ('timestamp', 'not-a-date', 'invalid')],
)
def test_location_horizon_rejects_invalid_inputs_before_observing(client, horizon_inputs, field, value, expected_code):
	url, parameters, observations = horizon_inputs
	parameters[field] = value
	response = client.get(url, parameters)
	assert_validation_error(response, field, expected_code)
	assert observations == []


def test_location_horizon_hides_loading_datasets(client, analysis_dataset, horizon_inputs):
	url, parameters, observations = horizon_inputs
	analysis_dataset.status = TerrainDataset.Status.LOADING
	analysis_dataset.save()

	assert client.get(url, parameters).status_code == 404
	assert observations == []


@pytest.mark.parametrize('error,status_code', [(EphemerisUnavailable('Kernels missing'), 503), (EphemerisTimeError('Outside kernel coverage'), 400)])
def test_location_horizon_reports_ephemeris_errors(client, horizon_inputs, monkeypatch, error, status_code):
	url, parameters, _ = horizon_inputs
	client.raise_request_exception = False

	def unavailable(times, position):
		raise error

	monkeypatch.setattr('terrain.services.surface_directions.calculate_surface_body_series', unavailable)

	response = client.get(url, parameters)

	assert response.status_code == status_code
	assert response.data['errors'][0]['detail'] == str(error)

	if status_code == 400:
		assert_validation_error(response, 'timestamp', 'invalid')
