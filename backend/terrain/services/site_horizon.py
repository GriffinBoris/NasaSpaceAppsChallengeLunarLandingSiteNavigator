import numpy

from terrain.services.body_geometry import body_angles
from terrain.services.horizon_profile import HorizonProfile, local_basis
from terrain.services.horizon_storage import load_profiles
from terrain.services.surface_directions import surface_directions

DISPLAY_BIN_COUNT = 512


def cached_horizon(dataset, latitude, longitude):
	latitude_radians = numpy.radians(latitude)
	longitude_radians = numpy.radians(longitude)
	position = numpy.array(
		[
			numpy.cos(latitude_radians) * numpy.cos(longitude_radians),
			numpy.cos(latitude_radians) * numpy.sin(longitude_radians),
			numpy.sin(latitude_radians),
		]
	)
	_, azimuth_offset = body_angles(position, latitude, longitude, local_basis(position)[:, 1])
	result = {'azimuth_offset_degrees': azimuth_offset, 'bounds': None}
	content = load_profiles(dataset, [(latitude, longitude)])[0]

	if content is None:
		return result

	profile = HorizonProfile.decode(content)

	if numpy.all(profile.lower == -numpy.pi / 2) and numpy.all(profile.upper == numpy.pi / 2):
		return result

	lower = profile.lower.reshape(DISPLAY_BIN_COUNT, -1).min(axis=1)
	upper = profile.upper.reshape(DISPLAY_BIN_COUNT, -1).max(axis=1)
	result['bounds'] = {'lower_elevation_degrees': numpy.degrees(lower).tolist(), 'upper_elevation_degrees': numpy.degrees(upper).tolist()}

	return result


def site_horizon(dataset, selection):
	return {'selection_id': selection['id'], **cached_horizon(dataset, selection['latitude'], selection['longitude'])}


def location_horizon(dataset, timestamp, latitude, longitude):
	directions = surface_directions(dataset, latitude, longitude, [timestamp])
	result = {
		'dataset_id': dataset.pk,
		'timestamp': timestamp,
		'latitude': latitude,
		'longitude': longitude,
		**cached_horizon(dataset, latitude, longitude),
	}

	for body, angles in directions.items():
		result[body] = {'elevation_degrees': angles['elevation_degrees'][0], 'azimuth_degrees': angles['azimuth_degrees'][0]}

	return result
