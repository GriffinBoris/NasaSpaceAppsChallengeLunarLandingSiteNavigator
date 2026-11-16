import numpy
from ephemeris.services.positions import calculate_surface_sun

from terrain.services.body_geometry import body_angles
from terrain.services.disk_visibility import calculate_disk_visibility
from terrain.services.open3d_surface_mesh import Open3DSurfaceMesh
from terrain.services.terrain_surface import TerrainSurface


def calculate_visibility(surface, position, normal, sun_vector, sun_radius):
	visibility = calculate_disk_visibility(surface, position, normal, sun_vector, sun_radius)

	return {
		'sun_angular_radius_degrees': visibility['angular_radius_degrees'],
		'visible_sun_fraction': visibility['visible_fraction'],
		'disk_sample_count': visibility['disk_sample_count'],
		'sampling_converged': visibility['sampling_converged'],
		'fraction_tolerance': visibility['fraction_tolerance'],
	}


class IlluminationPoint:
	def __init__(self, surface, latitude, longitude, geometry=None):
		self.surface = surface
		self.latitude = latitude
		self.longitude = longitude

		if geometry is None:
			self.position, self.normal, self.level = surface.surface_point(latitude, longitude)
		else:
			self.position = numpy.array(geometry['position'], dtype=numpy.float64)
			self.normal = numpy.array(geometry['normal'], dtype=numpy.float64)
			self.level = geometry['level']

	def geometry(self):
		return {
			'latitude': self.latitude,
			'longitude': self.longitude,
			'position': self.position.tolist(),
			'normal': self.normal.tolist(),
			'level': self.level,
		}

	def metadata(self, timestamp):
		dataset = self.surface.dataset

		return {
			'dataset_id': dataset.id,
			'timestamp': timestamp,
			'latitude': self.latitude,
			'longitude': self.longitude,
			'frame': dataset.frame,
			'elevation_meters': float(numpy.linalg.norm(self.position) - dataset.reference_radius),
			'analysis_level': self.level,
		}

	def result(self, timestamp, sun_vector, visibility):
		sun_direction = sun_vector / numpy.linalg.norm(sun_vector)
		elevation, azimuth = body_angles(self.position, self.latitude, self.longitude, sun_direction)

		return {
			**self.metadata(timestamp),
			'sun_elevation_degrees': elevation,
			'sun_azimuth_degrees': azimuth,
			**visibility,
		}

	def calculate(self, timestamp):
		sun_vector, sun_radius = calculate_surface_sun(timestamp, self.position)
		visibility = calculate_visibility(self.surface, self.position, self.normal, sun_vector, sun_radius)

		return self.result(timestamp, sun_vector, visibility)


def calculate_illumination(dataset, timestamp, latitude, longitude, mesh_class=Open3DSurfaceMesh):
	surface = TerrainSurface(dataset, mesh_class)
	point = IlluminationPoint(surface, latitude, longitude)

	return point.calculate(timestamp)
