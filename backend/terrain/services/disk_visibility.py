import numpy

from terrain.services.body_geometry import disk_directions
from terrain.services.surface_mesh import MINIMUM_INTERSECTION_DISTANCE

DISK_SAMPLE_COUNTS = (256, 1024, 4096)
VISIBLE_FRACTION_TOLERANCE = 0.005


def calculate_disk_visibility(surface, position, normal, body_vector, body_radius):
	origin = position + normal * MINIMUM_INTERSECTION_DISTANCE
	previous_fraction = None
	converged = False

	for sample_count in DISK_SAMPLE_COUNTS:
		directions, angular_radius = disk_directions(body_vector, body_radius, sample_count)
		visible = ~surface.blocked_rays(origin, directions)
		visible_fraction = float(visible.mean())

		if previous_fraction is not None and abs(visible_fraction - previous_fraction) <= VISIBLE_FRACTION_TOLERANCE:
			converged = True
			break

		previous_fraction = visible_fraction

	return {
		'angular_radius_degrees': float(numpy.degrees(angular_radius)),
		'visible_fraction': visible_fraction,
		'disk_sample_count': sample_count,
		'sampling_converged': converged,
		'fraction_tolerance': VISIBLE_FRACTION_TOLERANCE,
	}
