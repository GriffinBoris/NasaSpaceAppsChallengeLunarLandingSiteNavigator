import numpy
from ephemeris.services.positions import calculate_surface_body_series

from terrain.services.body_geometry import body_angles
from terrain.services.terrain_surface import TerrainSurface


def surface_directions(dataset, latitude, longitude, times):
	position = TerrainSurface(dataset).surface_point(latitude, longitude)[0]
	body_vectors = calculate_surface_body_series(times, position)
	directions = {}

	for body, vectors in body_vectors.items():
		angles = [body_angles(position, latitude, longitude, vector / numpy.linalg.norm(vector)) for vector in vectors]
		directions[body.lower()] = {
			'elevation_degrees': [round(elevation, 3) for elevation, _ in angles],
			'azimuth_degrees': [round(azimuth, 3) for _, azimuth in angles],
		}

	return directions
