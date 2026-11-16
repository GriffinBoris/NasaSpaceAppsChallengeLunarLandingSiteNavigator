import numpy

from terrain.services.illumination_patch import DEFAULT_RADIUS_METERS, PATCH_GRID_SIZE, patch_locations
from terrain.services.study_schedule import timestamps
from terrain.services.surface_directions import surface_directions
from terrain.services.terrain_surface import TerrainSurface

TERRAIN_GRID_SIZE = (PATCH_GRID_SIZE - 1) * 4 + 1


def site_terrain(dataset, selection):
	radius_meters = selection['radius_meters'] or DEFAULT_RADIUS_METERS
	surface = TerrainSurface(dataset)
	locations = patch_locations(
		selection['latitude'], selection['longitude'], radius_meters, dataset.reference_radius, TERRAIN_GRID_SIZE, clip_to_circle=False
	)
	heights = []

	for latitude, longitude in locations:
		position, _, _ = surface.surface_point(latitude, longitude)
		elevation_meters = float(numpy.linalg.norm(position) - dataset.reference_radius)
		heights.append(round(elevation_meters, 1))

	return {
		'selection_id': selection['id'],
		'radius_meters': radius_meters,
		'grid_size': TERRAIN_GRID_SIZE,
		'spacing_meters': 2 * radius_meters / (TERRAIN_GRID_SIZE - 1),
		'reference_radius_meters': dataset.reference_radius,
		'heights_meters': heights,
	}


def site_directions(study, selection):
	times = timestamps(study.start_time, study.end_time, study.step_seconds)
	directions = surface_directions(study.dataset, selection['latitude'], selection['longitude'], times)

	return {'selection_id': selection['id'], **directions}
