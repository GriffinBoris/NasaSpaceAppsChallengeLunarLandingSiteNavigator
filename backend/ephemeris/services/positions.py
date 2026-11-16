import logging
from contextlib import contextmanager
from threading import Lock

import spiceypy
from core.lunar import LUNAR_FRAME
from spiceypy.utils.exceptions import SpiceyError

from ephemeris.services.kernels import kernel_paths

logger = logging.getLogger(__name__)
SPICE_LOCK = Lock()


class EphemerisUnavailable(Exception):
	pass


class EphemerisTimeError(ValueError):
	pass


def _validated_ephemeris_times(timestamps):
	orientation_path = next(path for path in kernel_paths() if path.suffix == '.bpc')
	coverage = spiceypy.pckcov(str(orientation_path), 31006)
	coverage_start, coverage_end = spiceypy.wnfetd(coverage, 0)
	ephemeris_times = []

	for timestamp in timestamps:
		ephemeris_time = spiceypy.datetime2et(timestamp)

		if not coverage_start <= ephemeris_time <= coverage_end:
			start = spiceypy.et2utc(coverage_start, 'ISOC', 0)
			end = spiceypy.et2utc(coverage_end, 'ISOC', 0)

			raise EphemerisTimeError(f'Time must be between {start} UTC and {end} UTC.')

		ephemeris_times.append(ephemeris_time)

	return ephemeris_times


@contextmanager
def loaded_ephemeris(timestamp):
	paths = kernel_paths()

	if any(not path.is_file() for path in paths):
		raise EphemerisUnavailable('SPICE data is missing. Run task docker:backend:ephemeris:download.')

	with SPICE_LOCK:
		try:
			with spiceypy.KernelPool([str(path) for path in paths]):
				yield _validated_ephemeris_times([timestamp])[0]
		except SpiceyError as error:
			logger.warning('SPICE position calculation failed', exc_info=True)
			raise EphemerisUnavailable('SPICE data could not be read. Check the downloaded ephemeris kernels.') from error


def calculate_positions(timestamp):
	with loaded_ephemeris(timestamp) as ephemeris_time:
		bodies = {}

		for body_name in ('SUN', 'EARTH'):
			position, _ = spiceypy.spkpos(body_name, ephemeris_time, LUNAR_FRAME, 'LT+S', 'MOON')
			_, radii = spiceypy.bodvrd(body_name, 'RADII', 3)
			bodies[body_name.lower()] = {
				'position_km': position.tolist(),
				'radius_km': float(radii.mean()),
			}

		return {'timestamp': timestamp, 'frame': LUNAR_FRAME, **bodies}


def calculate_surface_sun(timestamp, position_meters):
	vectors, radius = calculate_surface_suns(timestamp, [position_meters])

	return vectors[0], radius


def calculate_surface_suns(timestamp, positions_meters):
	return calculate_surface_bodies(timestamp, positions_meters, 'SUN')


def calculate_surface_earths(timestamp, positions_meters):
	return calculate_surface_bodies(timestamp, positions_meters, 'EARTH')


def calculate_surface_bodies(timestamp, positions_meters, target):
	with loaded_ephemeris(timestamp) as ephemeris_time:
		vectors = []

		for position_meters in positions_meters:
			state, _ = spiceypy.spkcpo(target, ephemeris_time, LUNAR_FRAME, 'OBSERVER', 'CN+S', position_meters / 1000, 'MOON', LUNAR_FRAME)
			vectors.append(state[:3] * 1000)

		_, radii = spiceypy.bodvrd(target, 'RADII', 3)

		return vectors, float(radii.mean()) * 1000


def calculate_surface_body_series(timestamps, position_meters):
	with loaded_ephemeris(timestamps[0]):
		ephemeris_times = _validated_ephemeris_times(timestamps)
		body_vectors = {'SUN': [], 'EARTH': []}

		for ephemeris_time in ephemeris_times:
			for body, vectors in body_vectors.items():
				state, _ = spiceypy.spkcpo(body, ephemeris_time, LUNAR_FRAME, 'OBSERVER', 'CN+S', position_meters / 1000, 'MOON', LUNAR_FRAME)
				vectors.append(state[:3] * 1000)

		return body_vectors
