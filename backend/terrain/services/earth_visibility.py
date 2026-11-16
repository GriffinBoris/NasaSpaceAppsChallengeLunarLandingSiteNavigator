import numpy
from ephemeris.services.positions import calculate_surface_earths

from terrain.services.body_geometry import body_angles
from terrain.services.disk_visibility import calculate_disk_visibility
from terrain.services.illumination import IlluminationPoint
from terrain.services.illumination_patch import IlluminationRegion, progress_event
from terrain.services.open3d_surface_mesh import Open3DSurfaceMesh
from terrain.services.surface_mesh import MINIMUM_INTERSECTION_DISTANCE
from terrain.services.terrain_surface import TerrainSurface


def calculate_earth_visibility(surface, position, normal, earth_vector, earth_radius):
	visibility = calculate_disk_visibility(surface, position, normal, earth_vector, earth_radius)
	center_direction = earth_vector / numpy.linalg.norm(earth_vector)
	origin = position + normal * MINIMUM_INTERSECTION_DISTANCE
	center_blocked = surface.blocked_rays(origin, center_direction[None, :])[0]

	return {
		'earth_angular_radius_degrees': visibility['angular_radius_degrees'],
		'visible_earth_fraction': visibility['visible_fraction'],
		'earth_center_visible': not bool(center_blocked),
		'disk_sample_count': visibility['disk_sample_count'],
		'sampling_converged': visibility['sampling_converged'],
		'fraction_tolerance': visibility['fraction_tolerance'],
	}


def point_result(point, timestamp, earth_vector, visibility):
	earth_direction = earth_vector / numpy.linalg.norm(earth_vector)
	elevation, azimuth = body_angles(point.position, point.latitude, point.longitude, earth_direction)

	return {
		**point.metadata(timestamp),
		'earth_elevation_degrees': elevation,
		'earth_azimuth_degrees': azimuth,
		**visibility,
	}


def region_result(region, timestamp, earth_vectors, visibilities):
	points = [None] * len(region.locations)

	for index, visibility in zip(region.selected_indices, visibilities, strict=True):
		points[index] = {
			'visible_earth_fraction': visibility['visible_earth_fraction'],
			'earth_center_visible': visibility['earth_center_visible'],
			'sampling_converged': visibility['sampling_converged'],
		}

	center = point_result(region.points[region.center_index], timestamp, earth_vectors[region.center_index], visibilities[region.center_index])

	return {
		'center': center,
		'grid_size': region.grid_size,
		'radius_meters': region.radius_meters,
		'spacing_meters': 2 * region.radius_meters / (region.grid_size - 1),
		'points': points,
	}


def calculate_earth_point(dataset, timestamp, latitude, longitude):
	surface = TerrainSurface(dataset, Open3DSurfaceMesh)
	point = IlluminationPoint(surface, latitude, longitude)
	earth_vectors, earth_radius = calculate_surface_earths(timestamp, [point.position])
	visibility = calculate_earth_visibility(surface, point.position, point.normal, earth_vectors[0], earth_radius)

	return point_result(point, timestamp, earth_vectors[0], visibility)


def iter_earth_patch(dataset, timestamp, latitude, longitude, radius_meters):
	yield progress_event(0, 1, 'Preparing terrain')

	surface = TerrainSurface(dataset, Open3DSurfaceMesh)
	region = IlluminationRegion(surface, latitude, longitude, radius_meters)
	surface_positions = [point.position for point in region.points]
	earth_vectors, earth_radius = calculate_surface_earths(timestamp, surface_positions)
	visibilities = []
	total = len(region.points)

	for completed, (point, vector) in enumerate(zip(region.points, earth_vectors, strict=True), start=1):
		visibility = calculate_earth_visibility(surface, point.position, point.normal, vector, earth_radius)
		visibilities.append(visibility)

		yield progress_event(completed, total, 'Tracing Earth visibility')

	yield {'type': 'result', 'result': region_result(region, timestamp, earth_vectors, visibilities)}
