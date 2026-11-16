import numpy
from ephemeris.services.positions import calculate_surface_suns

from terrain.services.illumination import IlluminationPoint, calculate_visibility
from terrain.services.open3d_surface_mesh import Open3DSurfaceMesh
from terrain.services.surface_coordinates import surface_direction
from terrain.services.terrain_surface import TerrainSurface

PATCH_GRID_SIZE = 33
DEFAULT_RADIUS_METERS = 5000
MINIMUM_RADIUS_METERS = 250
MAXIMUM_RADIUS_METERS = 50000


def patch_locations(latitude, longitude, radius_meters, reference_radius, grid_size=None, clip_to_circle=True):
	if grid_size is None:
		grid_size = PATCH_GRID_SIZE

	center = surface_direction(latitude, longitude)
	longitude_radians = numpy.radians(longitude)
	east = numpy.array([-numpy.sin(longitude_radians), numpy.cos(longitude_radians), 0])
	north = numpy.cross(center, east)
	offsets = numpy.linspace(-radius_meters, radius_meters, grid_size)
	locations = []

	for north_offset in offsets[::-1]:
		for east_offset in offsets:
			tangent = north * north_offset + east * east_offset
			distance = numpy.hypot(north_offset, east_offset)

			if clip_to_circle and distance > radius_meters:
				locations.append(None)
				continue

			if distance == 0:
				locations.append((latitude, longitude))
				continue

			angle = distance / reference_radius
			direction = center * numpy.cos(angle) + tangent / distance * numpy.sin(angle)

			point_latitude = float(numpy.degrees(numpy.arcsin(numpy.clip(direction[2], -1, 1))))
			point_longitude = float(numpy.degrees(numpy.arctan2(direction[1], direction[0])))

			locations.append((point_latitude, point_longitude))

	return locations


def progress_event(completed, total, stage):
	return {
		'type': 'progress',
		'progress': {'completed': completed, 'total': total, 'percentage': completed * 100 // total, 'stage': stage},
	}


class IlluminationRegion:
	def __init__(self, surface, latitude, longitude, radius_meters, grid_size=None, samples=None):
		self.surface = surface
		self.radius_meters = radius_meters
		self.grid_size = grid_size

		if self.grid_size is None:
			self.grid_size = PATCH_GRID_SIZE

		if samples is None:
			self.locations = patch_locations(latitude, longitude, radius_meters, surface.dataset.reference_radius, self.grid_size)
			samples = [None] * len(self.locations)
		else:
			self.locations = []

			for sample in samples:
				if sample is None:
					self.locations.append(None)
				else:
					self.locations.append((sample['latitude'], sample['longitude']))

		self.selected_indices = [index for index, location in enumerate(self.locations) if location is not None]
		self.points = []

		for sample_index in self.selected_indices:
			point_latitude, point_longitude = self.locations[sample_index]
			point = IlluminationPoint(surface, point_latitude, point_longitude, geometry=samples[sample_index])
			self.points.append(point)

		self.center_index = self.selected_indices.index(len(self.locations) // 2)

	def result(self, timestamp, sun_vectors, visibilities):
		points = [None] * len(self.locations)

		for index, visibility in zip(self.selected_indices, visibilities, strict=True):
			points[index] = {
				'visible_sun_fraction': visibility['visible_sun_fraction'],
				'sampling_converged': visibility['sampling_converged'],
			}

		center_point = self.points[self.center_index]
		center = center_point.result(timestamp, sun_vectors[self.center_index], visibilities[self.center_index])

		return {
			'center': center,
			'grid_size': self.grid_size,
			'radius_meters': self.radius_meters,
			'spacing_meters': 2 * self.radius_meters / (self.grid_size - 1),
			'points': points,
		}

	def iter_calculation(self, timestamp):
		total = len(self.points) + 1
		progress_interval = max(1, total // 100)

		yield progress_event(0, total, 'Locating the Sun')

		positions = [point.position for point in self.points]
		sun_vectors, sun_radius = calculate_surface_suns(timestamp, positions)
		visibilities = []

		for completed, (point, sun_vector) in enumerate(zip(self.points, sun_vectors, strict=True), start=1):
			visibility = calculate_visibility(self.surface, point.position, point.normal, sun_vector, sun_radius)
			visibilities.append(visibility)

			if completed % progress_interval == 0 or completed == total - 1:
				yield progress_event(completed, total, 'Tracing sunlight')

		yield progress_event(total - 1, total, 'Finishing the result')

		yield progress_event(total, total, 'Complete')

		yield {'type': 'result', 'result': self.result(timestamp, sun_vectors, visibilities)}


def iter_illumination_patch(dataset, timestamp, latitude, longitude, radius_meters, mesh_class=Open3DSurfaceMesh):
	locations = patch_locations(latitude, longitude, radius_meters, dataset.reference_radius)
	total = sum(location is not None for location in locations) + 1

	yield progress_event(0, total, 'Preparing terrain')

	surface = TerrainSurface(dataset, mesh_class)
	region = IlluminationRegion(surface, latitude, longitude, radius_meters)

	yield from region.iter_calculation(timestamp)
