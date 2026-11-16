from concurrent.futures import CancelledError

from terrain.models.TerrainDataset import TerrainDataset
from terrain.services.earth_visibility import calculate_earth_visibility
from terrain.services.horizon_surface import HorizonSurface
from terrain.services.illumination import IlluminationPoint, calculate_visibility
from terrain.services.open3d_surface_mesh import Open3DSurfaceMesh
from terrain.services.terrain_surface import TerrainSurface


class SunlightSamples:
	def __init__(self, dataset_id, locations, stop_event, geometry=None):
		self.stop_event = stop_event
		dataset = TerrainDataset.objects.get(pk=dataset_id, status=TerrainDataset.Status.READY)
		self.surface = HorizonSurface(TerrainSurface(dataset, Open3DSurfaceMesh))

		if geometry is None:
			geometry = [None] * len(locations)

		self.points = [
			IlluminationPoint(self.surface, latitude, longitude, geometry=sample)
			for (latitude, longitude), sample in zip(locations, geometry, strict=True)
		]

	def prepare_profile(self, index, content):
		if self.stop_event.is_set():
			raise CancelledError()

		if index is None:
			return

		point = self.points[index]

		return self.surface.prepare_profile(point.position, point.normal, content)

	def calculate(self, body_vectors, body_radius, body='SUN'):
		results = []
		visibility_function = {'SUN': calculate_visibility, 'EARTH': calculate_earth_visibility}[body]

		for point, body_vector in zip(self.points, body_vectors, strict=True):
			if self.stop_event.is_set():
				raise CancelledError()

			results.append(visibility_function(self.surface, point.position, point.normal, body_vector, body_radius))

		return results
