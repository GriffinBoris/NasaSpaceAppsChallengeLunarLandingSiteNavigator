from contextlib import contextmanager
from datetime import UTC, datetime

import numpy
import pytest
import spiceypy
from spiceypy.utils.exceptions import SpiceyError
from terrain.services.body_geometry import body_angles
from terrain.services.surface_coordinates import surface_direction

from ephemeris.services.kernels import kernel_paths
from ephemeris.services.positions import (
	EphemerisTimeError,
	EphemerisUnavailable,
	calculate_positions,
	calculate_surface_body_series,
	calculate_surface_earths,
	calculate_surface_sun,
	calculate_surface_suns,
)


@pytest.fixture
def fake_spice(settings, tmp_path, monkeypatch):
	settings.SPICE_ROOT = tmp_path

	for path in kernel_paths():
		path.touch()

	events = []

	@contextmanager
	def kernel_pool(paths):
		events.append('loaded')

		try:
			yield
		finally:
			events.append('unloaded')

	def position(body, timestamp, frame, correction, observer):
		assert frame == 'MOON_ME_DE421'
		assert correction == 'LT+S'
		assert observer == 'MOON'

		return numpy.array([100, 200, 300]) if body == 'SUN' else numpy.array([400, 500, 600]), 0

	monkeypatch.setattr('ephemeris.services.positions.spiceypy.KernelPool', kernel_pool)
	monkeypatch.setattr('ephemeris.services.positions.spiceypy.datetime2et', lambda timestamp: 0)
	monkeypatch.setattr('ephemeris.services.positions.spiceypy.pckcov', lambda path, frame: None)
	monkeypatch.setattr('ephemeris.services.positions.spiceypy.wnfetd', lambda coverage, index: (-100, 100))
	monkeypatch.setattr('ephemeris.services.positions.spiceypy.spkpos', position)
	monkeypatch.setattr('ephemeris.services.positions.spiceypy.bodvrd', lambda body, item, count: (3, numpy.array([3, 6, 9])))

	return events


def test_positions_preserve_kilometers_and_release_kernels(fake_spice):
	timestamp = datetime(2026, 11, 11, 12, tzinfo=UTC)

	positions = calculate_positions(timestamp)

	assert positions == {
		'timestamp': timestamp,
		'frame': 'MOON_ME_DE421',
		'sun': {'position_km': [100, 200, 300], 'radius_km': 6},
		'earth': {'position_km': [400, 500, 600], 'radius_km': 6},
	}
	assert fake_spice == ['loaded', 'unloaded']


def test_series_rejects_later_uncovered_time_before_querying_and_releases_kernels(fake_spice, monkeypatch):
	monkeypatch.setattr('ephemeris.services.positions.spiceypy.datetime2et', lambda timestamp: (timestamp.day - 11) * 101)
	monkeypatch.setattr('ephemeris.services.positions.spiceypy.et2utc', lambda timestamp, format, precision: 'coverage boundary')
	queries = []
	monkeypatch.setattr('ephemeris.services.positions.spiceypy.spkcpo', lambda *arguments: queries.append(arguments))
	timestamps = [datetime(2026, 11, day, tzinfo=UTC) for day in (11, 12)]

	with pytest.raises(EphemerisTimeError, match='Time must be between'):
		calculate_surface_body_series(timestamps, numpy.array([1737400.0, 0, 0]))

	assert queries == []
	assert fake_spice == ['loaded', 'unloaded']


def test_out_of_coverage_time_releases_kernels(fake_spice, monkeypatch):
	monkeypatch.setattr('ephemeris.services.positions.spiceypy.datetime2et', lambda timestamp: 101)
	monkeypatch.setattr('ephemeris.services.positions.spiceypy.et2utc', lambda timestamp, format, precision: 'coverage boundary')

	with pytest.raises(EphemerisTimeError, match='Time must be between'):
		calculate_positions(datetime(2100, 1, 1, tzinfo=UTC))

	assert fake_spice == ['loaded', 'unloaded']


def test_failed_query_releases_kernels_and_allows_retry(fake_spice, monkeypatch):
	original_position = spiceypy.spkpos

	def fail_query(body, timestamp, frame, correction, observer):
		raise SpiceyError('Unreadable kernel')

	monkeypatch.setattr('ephemeris.services.positions.spiceypy.spkpos', fail_query)

	with pytest.raises(EphemerisUnavailable, match='could not be read'):
		calculate_positions(datetime(2026, 11, 11, tzinfo=UTC))

	monkeypatch.setattr('ephemeris.services.positions.spiceypy.spkpos', original_position)
	assert calculate_positions(datetime(2026, 11, 11, tzinfo=UTC))['earth']['position_km'] == [400, 500, 600]
	assert fake_spice == ['loaded', 'unloaded', 'loaded', 'unloaded']


def test_real_kernels_match_de421_reference_vectors():
	if any(not path.is_file() for path in kernel_paths()):
		pytest.skip('Run task docker:backend:ephemeris:download to verify real kernels.')

	positions = calculate_positions(datetime(2026, 11, 11, 12, tzinfo=UTC))

	numpy.testing.assert_allclose(positions['earth']['position_km'], [400647.5232721022, 13681.04108976808, 43870.282046027336], rtol=0, atol=0.001)
	numpy.testing.assert_allclose(positions['sun']['position_km'], [-136064350.65459937, 57464679.00061333, -4002894.860645655], rtol=0, atol=0.01)
	assert positions['sun']['radius_km'] == 695700
	assert spiceypy.ktotal('ALL') == 0


def test_surface_sun_uses_the_site_position_and_returns_meters(fake_spice, monkeypatch):
	def surface_position(target, timestamp, output_frame, frame_epoch, corrections, observer_position, observer_center, observer_frame):
		assert target == 'SUN'
		assert output_frame == observer_frame == 'MOON_ME_DE421'
		assert frame_epoch == 'OBSERVER'
		assert corrections == 'CN+S'
		assert observer_center == 'MOON'
		numpy.testing.assert_array_equal(observer_position, [1737.4, 0, 0])

		return numpy.array([100.0, 200, 300, 0, 0, 0]), 0

	monkeypatch.setattr('ephemeris.services.positions.spiceypy.spkcpo', surface_position)

	position, radius = calculate_surface_sun(datetime(2026, 11, 11, tzinfo=UTC), numpy.array([1737400.0, 0, 0]))

	numpy.testing.assert_array_equal(position, [100000, 200000, 300000])
	assert radius == 6000
	assert fake_spice == ['loaded', 'unloaded']


def test_surface_sun_releases_kernels_on_failure_and_can_retry(fake_spice, monkeypatch):
	def fail_query(*arguments):
		raise SpiceyError('Unreadable surface ephemeris')

	monkeypatch.setattr('ephemeris.services.positions.spiceypy.spkcpo', fail_query)

	with pytest.raises(EphemerisUnavailable, match='could not be read'):
		calculate_surface_sun(datetime(2026, 11, 11, tzinfo=UTC), numpy.array([1737400.0, 0, 0]))

	monkeypatch.setattr('ephemeris.services.positions.spiceypy.spkcpo', lambda *arguments: (numpy.ones(6), 0))
	calculate_surface_sun(datetime(2026, 11, 11, tzinfo=UTC), numpy.array([1737400.0, 0, 0]))

	assert fake_spice == ['loaded', 'unloaded', 'loaded', 'unloaded']


def test_surface_sun_batch_uses_each_site_under_one_kernel_pool(fake_spice, monkeypatch):
	observers = []

	def surface_position(target, timestamp, output_frame, frame_epoch, corrections, observer_position, observer_center, observer_frame):
		assert corrections == 'CN+S'
		observers.append(observer_position.copy())

		return numpy.array([100.0, 200, 300, 0, 0, 0]), 0

	monkeypatch.setattr('ephemeris.services.positions.spiceypy.spkcpo', surface_position)
	positions = [numpy.array([1737400.0, 0, 0]), numpy.array([0.0, 0, -1737400])]

	vectors, radius = calculate_surface_suns(datetime(2026, 11, 11, tzinfo=UTC), positions)

	numpy.testing.assert_array_equal(observers, [[1737.4, 0, 0], [0, 0, -1737.4]])
	numpy.testing.assert_array_equal(vectors, [[100000, 200000, 300000], [100000, 200000, 300000]])
	assert radius == 6000
	assert fake_spice == ['loaded', 'unloaded']


def test_surface_earth_batch_uses_lunar_observers_and_apparent_positions(fake_spice, monkeypatch):
	observers = []

	def surface_position(target, timestamp, output_frame, frame_epoch, corrections, observer_position, observer_center, observer_frame):
		assert target == 'EARTH'
		assert output_frame == observer_frame == 'MOON_ME_DE421'
		assert frame_epoch == 'OBSERVER'
		assert corrections == 'CN+S'
		assert observer_center == 'MOON'
		observers.append(observer_position.copy())

		return numpy.array([384400.0, 200, 300, 0, 0, 0]), 0

	monkeypatch.setattr('ephemeris.services.positions.spiceypy.spkcpo', surface_position)
	positions = [numpy.array([1737400.0, 0, 0]), numpy.array([0.0, 0, -1737400])]
	vectors, radius = calculate_surface_earths(datetime(2026, 11, 11, tzinfo=UTC), positions)

	numpy.testing.assert_array_equal(observers, [[1737.4, 0, 0], [0, 0, -1737.4]])
	numpy.testing.assert_array_equal(vectors, [[384400000, 200000, 300000], [384400000, 200000, 300000]])
	assert radius == 6000
	assert fake_spice == ['loaded', 'unloaded']


@pytest.mark.parametrize('day,azimuth,elevation', [(11, 181.956118949, -6.590443797), (18, 173.368298823, 1.038821638)])
def test_surface_earth_matches_horizons_mean_earth_reference_angles(day, azimuth, elevation):
	if any(not path.is_file() for path in kernel_paths()):
		pytest.skip('Run task docker:backend:ephemeris:download to verify real kernels.')

	position = surface_direction(-89.9, 180) * 1737400
	vectors, _ = calculate_surface_earths(datetime(2026, 11, day, 12, tzinfo=UTC), [position])
	direction = vectors[0] / numpy.linalg.norm(vectors[0])
	actual_elevation, actual_azimuth = body_angles(position, -89.9, 180, direction)

	assert actual_elevation == pytest.approx(elevation, abs=0.00005)
	assert actual_azimuth == pytest.approx(azimuth, abs=0.00005)


def test_surface_body_series_queries_both_bodies_at_every_time_under_one_kernel_pool(fake_spice, monkeypatch):
	queried = []

	def surface_position(target, ephemeris_time, output_frame, frame_epoch, corrections, observer_position, observer_center, observer_frame):
		queried.append((target, ephemeris_time))
		assert output_frame == observer_frame == 'MOON_ME_DE421'
		assert corrections == 'CN+S'
		offset = 1 if target == 'SUN' else 2

		return numpy.array([ephemeris_time, 0, offset, 0, 0, 0]), 0

	monkeypatch.setattr('ephemeris.services.positions.spiceypy.datetime2et', lambda timestamp: timestamp.hour)
	monkeypatch.setattr('ephemeris.services.positions.spiceypy.spkcpo', surface_position)
	times = [datetime(2026, 11, 11, hour, tzinfo=UTC) for hour in (0, 6, 12)]

	vectors = calculate_surface_body_series(times, numpy.array([1737400.0, 0, 0]))

	assert queried == [('SUN', 0), ('EARTH', 0), ('SUN', 6), ('EARTH', 6), ('SUN', 12), ('EARTH', 12)]
	numpy.testing.assert_array_equal(vectors['SUN'], [[0, 0, 1000], [6000, 0, 1000], [12000, 0, 1000]])
	numpy.testing.assert_array_equal(vectors['EARTH'], [[0, 0, 2000], [6000, 0, 2000], [12000, 0, 2000]])
	assert fake_spice == ['loaded', 'unloaded']
