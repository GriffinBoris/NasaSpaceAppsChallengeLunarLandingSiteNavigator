from terrain.services.horizon_builder import HorizonBuilder
from terrain.services.horizon_profile import HorizonProfile, local_basis
from terrain.services.surface_mesh import MINIMUM_INTERSECTION_DISTANCE


class HorizonSurface:
	def __init__(self, terrain):
		self.terrain = terrain
		self.dataset = terrain.dataset
		self.builder = None
		self.profiles = {}

	def surface_point(self, latitude, longitude):
		return self.terrain.surface_point(latitude, longitude)

	def prepare_profile(self, position, normal, content=None):
		origin = position + normal * MINIMUM_INTERSECTION_DISTANCE

		if origin.tobytes() in self.profiles:
			return

		if content is None:
			if self.builder is None:
				self.builder = HorizonBuilder(self.dataset)

			profile = self.builder.build(position, normal)
		else:
			profile = HorizonProfile.decode(content)

		self.profiles[origin.tobytes()] = profile, local_basis(position)

		if content is None:
			return profile.encode()

	def blocked_rays(self, origin, directions):
		prepared = self.profiles.get(origin.tobytes())

		if prepared is None:
			return self.terrain.blocked_rays(origin, directions)

		profile, basis = prepared
		blocked, uncertain = profile.classify(directions, basis)

		if uncertain.any():
			blocked[uncertain] = self.terrain.blocked_rays(origin, directions[uncertain])

		return blocked
