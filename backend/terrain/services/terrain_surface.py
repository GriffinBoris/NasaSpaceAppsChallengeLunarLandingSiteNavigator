from collections import OrderedDict

import numpy
from core.lunar import LUNAR_FRAME

from terrain.models.TerrainDataset import TerrainDataset
from terrain.services.surface_coordinates import face_coordinates, rays_cross_tile, surface_direction, tile_bounds
from terrain.services.surface_mesh import MINIMUM_INTERSECTION_DISTANCE, SurfaceMesh
from terrain.services.tile_encoding import HEIGHT_SCALE
from terrain.services.tile_reader import read_tile_heights


class TerrainAnalysisUnavailable(ValueError):
	pass


class TerrainSurface:
	def __init__(self, dataset, mesh_class=SurfaceMesh):
		if dataset.status != TerrainDataset.Status.READY or dataset.storage_format != TerrainDataset.StorageFormat.INT16_DELTA_GZIP:
			raise TerrainAnalysisUnavailable('Sunlight analysis requires a completed database terrain import with Int16 heights.')

		if dataset.frame != LUNAR_FRAME:
			raise TerrainAnalysisUnavailable('Terrain and sunlight must use the MOON_ME_DE421 frame.')

		self.mesh_class = mesh_class
		self.dataset = dataset
		self.refinements = set(dataset.refinements)
		self.meshes = OrderedDict()
		self.outer_radius = dataset.reference_radius + numpy.iinfo(numpy.int16).max * HEIGHT_SCALE + 1

	def mesh(self, coordinates):
		if coordinates in self.meshes:
			mesh = self.meshes.pop(coordinates)
		else:
			heights = read_tile_heights(self.dataset, *coordinates).reshape(self.dataset.tile_size, self.dataset.tile_size)
			mesh = self.mesh_class(coordinates, heights, self.dataset.reference_radius)

		self.meshes[coordinates] = mesh

		if len(self.meshes) > 128:
			self.meshes.popitem(last=False)

		return mesh

	def surface_point(self, latitude, longitude):
		direction = surface_direction(latitude, longitude)
		face, horizontal, vertical = face_coordinates(direction)
		level = 0
		tile_x = 0
		tile_y = 0

		while f'{face}/{level}/{tile_x}/{tile_y}' in self.refinements:
			level += 1
			divisions = 2**level
			tile_x = min(int((horizontal + 1) * divisions / 2), divisions - 1)
			tile_y = min(int((1 - vertical) * divisions / 2), divisions - 1)

		coordinates = (face, level, tile_x, tile_y)
		left, right, top, bottom = tile_bounds(level, tile_x, tile_y)
		horizontal_fraction = numpy.clip((horizontal - left) / (right - left), 0, 1)
		vertical_fraction = numpy.clip((top - vertical) / (top - bottom), 0, 1)
		position, normal = self.mesh(coordinates).surface_point(direction, horizontal_fraction, vertical_fraction)

		return position, normal, level

	def blocked_rays(self, origin, directions):
		blocked = numpy.zeros(len(directions), dtype=bool)

		if not len(directions):
			return blocked

		origin_projections = directions @ origin
		maximum_distances = -origin_projections + numpy.sqrt(origin_projections**2 + self.outer_radius**2 - origin @ origin)
		endpoints = origin + directions * maximum_distances[:, None]
		padding = MINIMUM_INTERSECTION_DISTANCE * 10
		bundle_minimum = numpy.minimum(origin, endpoints.min(axis=0)) - padding
		bundle_maximum = numpy.maximum(origin, endpoints.max(axis=0)) + padding
		cached = dict(self.meshes)

		for mesh in cached.values():
			if numpy.any(mesh.maximum_corner < bundle_minimum) or numpy.any(mesh.minimum_corner > bundle_maximum):
				continue

			ray_indices = numpy.flatnonzero(~blocked)

			if not len(ray_indices):
				return blocked

			blocked[ray_indices] = mesh.blocked_rays(origin, directions[ray_indices])

		pending = [((face, 0, 0, 0), numpy.arange(len(directions))) for face in range(6)]

		while pending:
			coordinates, ray_indices = pending.pop()
			ray_indices = ray_indices[~blocked[ray_indices]]

			if not len(ray_indices):
				continue

			selection = rays_cross_tile(origin, directions[ray_indices], coordinates, maximum_distances[ray_indices])
			ray_indices = ray_indices[selection]

			if not len(ray_indices):
				continue

			face, level, tile_x, tile_y = coordinates

			if f'{face}/{level}/{tile_x}/{tile_y}' not in self.refinements:
				if coordinates not in cached:
					blocked[ray_indices] = self.mesh(coordinates).blocked_rays(origin, directions[ray_indices])

				continue

			for child_y in range(2):
				for child_x in range(2):
					child = (face, level + 1, tile_x * 2 + child_x, tile_y * 2 + child_y)
					pending.append((child, ray_indices))

		return blocked
