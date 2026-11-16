import numpy

from terrain.services.surface_coordinates import cube_surface_directions, tile_bounds

MINIMUM_INTERSECTION_DISTANCE = 0.001


def triangle_distances(origin, directions, triangles):
	first_edges = triangles[:, 1] - triangles[:, 0]
	second_edges = triangles[:, 2] - triangles[:, 0]
	direction_cross_edges = numpy.cross(directions[:, None, :], second_edges)
	determinants = numpy.sum(first_edges * direction_cross_edges, axis=-1)
	inverse_determinants = numpy.zeros_like(determinants)

	numpy.divide(1, determinants, out=inverse_determinants, where=numpy.abs(determinants) > 1e-12)

	origin_offsets = origin - triangles[:, 0]
	first_weights = numpy.sum(origin_offsets * direction_cross_edges, axis=-1) * inverse_determinants
	offset_cross_edges = numpy.cross(origin_offsets, first_edges)
	second_weights = numpy.sum(directions[:, None, :] * offset_cross_edges, axis=-1) * inverse_determinants
	distances = numpy.sum(second_edges * offset_cross_edges, axis=-1) * inverse_determinants
	intersections = (
		(numpy.abs(determinants) > 1e-12)
		& (first_weights >= -1e-10)
		& (second_weights >= -1e-10)
		& (first_weights + second_weights <= 1 + 1e-10)
		& (distances > MINIMUM_INTERSECTION_DISTANCE)
	)

	return numpy.where(intersections, distances, numpy.inf)


def rays_cross_box(origin, directions, minimum_corner, maximum_corner):
	minimum_distances = numpy.zeros(len(directions))
	maximum_distances = numpy.full(len(directions), numpy.inf)

	for axis in range(3):
		rates = directions[:, axis]
		first_crossings = numpy.zeros(len(directions))
		second_crossings = numpy.zeros(len(directions))

		numpy.divide(minimum_corner[axis] - origin[axis], rates, out=first_crossings, where=rates != 0)
		numpy.divide(maximum_corner[axis] - origin[axis], rates, out=second_crossings, where=rates != 0)

		minimum_distances = numpy.where(
			rates != 0, numpy.maximum(minimum_distances, numpy.minimum(first_crossings, second_crossings)), minimum_distances
		)
		maximum_distances = numpy.where(
			rates != 0, numpy.minimum(maximum_distances, numpy.maximum(first_crossings, second_crossings)), maximum_distances
		)
		outside_parallel = (rates == 0) & ((origin[axis] < minimum_corner[axis]) | (origin[axis] > maximum_corner[axis]))
		maximum_distances[outside_parallel] = -1

	return maximum_distances >= minimum_distances


class SurfaceMesh:
	def __init__(self, coordinates, heights, reference_radius):
		face, level, tile_x, tile_y = coordinates
		left, right, top, bottom = tile_bounds(level, tile_x, tile_y)
		horizontal, vertical = numpy.meshgrid(numpy.linspace(left, right, heights.shape[1]), numpy.linspace(top, bottom, heights.shape[0]))
		directions = cube_surface_directions(face, horizontal, vertical)

		self.positions = directions * (reference_radius + heights[:, :, None])
		self.segment_count = heights.shape[0] - 1
		self.minimum_corner = self.positions.min(axis=(0, 1))
		self.maximum_corner = self.positions.max(axis=(0, 1))
		self.bounds = {(0, 0, self.segment_count, self.segment_count): (self.minimum_corner, self.maximum_corner)}

	def triangles(self, top, left, bottom, right):
		top_left = self.positions[top:bottom, left:right].reshape(-1, 3)
		top_right = self.positions[top:bottom, left + 1 : right + 1].reshape(-1, 3)
		bottom_left = self.positions[top + 1 : bottom + 1, left:right].reshape(-1, 3)
		bottom_right = self.positions[top + 1 : bottom + 1, left + 1 : right + 1].reshape(-1, 3)

		return numpy.concatenate(
			(numpy.stack((top_left, bottom_left, top_right), axis=1), numpy.stack((top_right, bottom_left, bottom_right), axis=1))
		)

	def surface_point(self, direction, horizontal_fraction, vertical_fraction):
		column = min(int(horizontal_fraction * self.segment_count), self.segment_count - 1)
		row = min(int(vertical_fraction * self.segment_count), self.segment_count - 1)
		triangles = self.triangles(row, column, row + 1, column + 1)
		distances = triangle_distances(numpy.zeros(3), direction[None, :], triangles)[0]
		triangle_index = numpy.argmin(distances)

		if not numpy.isfinite(distances[triangle_index]):
			raise ValueError('The location does not intersect its terrain cell.')

		triangle = triangles[triangle_index]
		normal = numpy.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])
		normal /= numpy.linalg.norm(normal)

		return direction * distances[triangle_index], normal

	def blocked_rays(self, origin, directions):
		blocked = numpy.zeros(len(directions), dtype=bool)
		pending = [(0, 0, self.segment_count, self.segment_count, numpy.arange(len(directions)))]

		while pending:
			top, left, bottom, right, ray_indices = pending.pop()
			ray_indices = ray_indices[~blocked[ray_indices]]

			if not len(ray_indices):
				continue

			key = (top, left, bottom, right)

			if key not in self.bounds:
				positions = self.positions[top : bottom + 1, left : right + 1]
				self.bounds[key] = (positions.min(axis=(0, 1)), positions.max(axis=(0, 1)))

			ray_indices = ray_indices[rays_cross_box(origin, directions[ray_indices], *self.bounds[key])]

			if not len(ray_indices):
				continue

			if bottom - top <= 4 and right - left <= 4:
				distances = triangle_distances(origin, directions[ray_indices], self.triangles(top, left, bottom, right))
				blocked[ray_indices] = numpy.isfinite(distances).any(axis=1)
				continue

			middle_row = (top + bottom) // 2
			middle_column = (left + right) // 2

			for first_row, last_row in ((top, middle_row), (middle_row, bottom)):
				for first_column, last_column in ((left, middle_column), (middle_column, right)):
					pending.append((first_row, first_column, last_row, last_column, ray_indices))

		return blocked
