from datetime import UTC, datetime

import pytest
from django.urls import reverse

from ephemeris.services.positions import EphemerisTimeError


@pytest.mark.parametrize('timestamp', [None, 'invalid'])
def test_timestamp_is_required_and_valid(client, timestamp):
	parameters = {} if timestamp is None else {'timestamp': timestamp}

	response = client.get(reverse('ephemeris:positions:ephemeris-detail'), parameters)

	assert response.status_code == 400
	assert response.data['errors'][0]['attr'] == 'timestamp'


def test_public_endpoint_returns_positions_at_utc_time(client, monkeypatch):
	def positions(timestamp):
		assert timestamp == datetime(2026, 11, 11, 12, tzinfo=UTC)

		return {
			'timestamp': timestamp,
			'frame': 'MOON_ME_DE421',
			'sun': {'position_km': [1, 2, 3], 'radius_km': 695700},
			'earth': {'position_km': [4, 5, 6], 'radius_km': 6371},
		}

	monkeypatch.setattr('ephemeris.views.positions.views.calculate_positions', positions)

	response = client.get(reverse('ephemeris:positions:ephemeris-detail'), {'timestamp': '2026-11-11T07:00:00-05:00'})

	assert response.status_code == 200
	assert response.data == {
		'timestamp': '2026-11-11T12:00:00Z',
		'frame': 'MOON_ME_DE421',
		'sun': {'position_km': [1, 2, 3], 'radius_km': 695700},
		'earth': {'position_km': [4, 5, 6], 'radius_km': 6371},
	}


def test_missing_kernels_return_service_unavailable(client, settings, tmp_path):
	settings.SPICE_ROOT = tmp_path
	client.raise_request_exception = False

	response = client.get(reverse('ephemeris:positions:ephemeris-detail'), {'timestamp': '2026-11-11T12:00:00Z'})

	assert response.status_code == 503
	assert response.data['errors'][0]['code'] == 'ephemeris_unavailable'
	assert 'task docker:backend:ephemeris:download' in response.data['errors'][0]['detail']


def test_out_of_coverage_time_returns_a_field_error(client, monkeypatch):
	def positions(timestamp):
		raise EphemerisTimeError('Time is outside the available coverage.')

	monkeypatch.setattr('ephemeris.views.positions.views.calculate_positions', positions)

	response = client.get(reverse('ephemeris:positions:ephemeris-detail'), {'timestamp': '2100-01-01T12:00:00Z'})

	assert response.status_code == 400
	assert response.data['errors'][0]['attr'] == 'timestamp'


def test_ephemeris_endpoint_has_no_write_actions(client):
	assert client.post(reverse('ephemeris:positions:ephemeris-detail'), {}).status_code == 405
