from heapq import heappop, heappush

import numpy

from terrain.services.horizon_profile import ANGLE_MARGIN, HORIZON_BIN_COUNT, HorizonProfile, local_basis
from terrain.services.surface_coordinates import tile_bounds
from terrain.services.surface_mesh import MINIMUM_INTERSECTION_DISTANCE
from terrain.services.terrain_surface import TerrainSurface
from terrain.services.tile_encoding import HEIGHT_SCALE
from terrain.services.tile_grid import cube_coordinates

BIN_WIDTH = 2 * numpy.pi / HORIZON_BIN_COUNT
BOX_CORNERS = numpy.array([[0, 0, 0], [0, 0, 1], [0, 1, 0], [0, 1, 1], [1, 0, 0], [1, 0, 1], [1, 1, 0], [1, 1, 1]])
BOUNDARY_DISTANCE = 0.01


def estimated_box(coordinates, minimum_radius, maximum_radius):
	face, level, tile_x, tile_y = coordinates
	left, right, top, bottom = tile_bounds(level, tile_x, tile_y)
	coordinate_x, coordinate_y, coordinate_z = cube_coordinates(
		face, numpy.array([left, right, right, left]), numpy.array([top, top, bottom, bottom])
	)
	corners = numpy.column_stack((coordinate_x, -coordinate_z, coordinate_y))
	minimum = corners.min(axis=0)
	maximum = corners.max(axis=0)
	nearest = numpy.where(minimum > 0, minimum, numpy.minimum(maximum, 0))
	minimum_norm = numpy.linalg.norm(nearest)
	maximum_norm = numpy.linalg.norm(numpy.maximum(numpy.abs(minimum), numpy.abs(maximum)))
	values = numpy.stack((minimum / minimum_norm, minimum / maximum_norm, maximum / minimum_norm, maximum / maximum_norm))
	values = numpy.concatenate((values * minimum_radius, values * maximum_radius))

	return values.min(axis=0) - 1e-6, values.max(axis=0) + 1e-6


def angular_box(minimum, maximum, origin, basis):
	corners = minimum + BOX_CORNERS * (maximum - minimum)
	local = (corners - origin) @ basis
	local_minimum = local.min(axis=0)
	local_maximum = local.max(axis=0)
	nearest = numpy.where(local_minimum[:2] > 0, local_minimum[:2], numpy.minimum(local_maximum[:2], 0))
	minimum_horizontal = numpy.linalg.norm(nearest)
	maximum_horizontal = numpy.linalg.norm(numpy.maximum(numpy.abs(local_minimum[:2]), numpy.abs(local_maximum[:2])))
	horizontal_distance = minimum_horizontal if local_maximum[2] >= 0 else maximum_horizontal
	maximum_elevation = numpy.arctan2(local_maximum[2], horizontal_distance) + ANGLE_MARGIN

	if minimum_horizontal == 0:
		return numpy.arange(HORIZON_BIN_COUNT), maximum_elevation

	azimuths = numpy.sort(numpy.arctan2(local[:, 0], local[:, 1]) % (2 * numpy.pi))
	gaps = numpy.diff(numpy.append(azimuths, azimuths[0] + 2 * numpy.pi))
	gap_index = numpy.argmax(gaps)
	start = azimuths[(gap_index + 1) % len(azimuths)]
	span = 2 * numpy.pi - gaps[gap_index]
	first_bin = int(numpy.floor((start - ANGLE_MARGIN) / BIN_WIDTH))
	last_bin = int(numpy.floor((start + span + ANGLE_MARGIN) / BIN_WIDTH))

	return numpy.arange(first_bin, last_bin + 1) % HORIZON_BIN_COUNT, maximum_elevation


def update_edges(lower, upper, first, second):
	edges = second - first
	weights = numpy.clip(-numpy.sum(first * edges, axis=1) / numpy.sum(edges * edges, axis=1), 0, 1)
	distances = numpy.linalg.norm(first + weights[:, None] * edges, axis=1)

	if numpy.any(distances <= BOUNDARY_DISTANCE):
		return False

	first_azimuths = numpy.arctan2(first[:, 0], first[:, 1]) % (2 * numpy.pi)
	second_azimuths = numpy.arctan2(second[:, 0], second[:, 1]) % (2 * numpy.pi)
	differences = (second_azimuths - first_azimuths + numpy.pi) % (2 * numpy.pi) - numpy.pi
	starts = numpy.where(differences >= 0, first_azimuths, second_azimuths)
	ends = starts + numpy.abs(differences)
	normals = numpy.cross(first, second)
	valid_edges = numpy.abs(normals[:, 2]) > 1e-8 * numpy.linalg.norm(normals, axis=1)
	east_coefficients = numpy.zeros(len(first))
	north_coefficients = numpy.zeros(len(first))
	numpy.divide(-normals[:, 0], normals[:, 2], out=east_coefficients, where=valid_edges)
	numpy.divide(-normals[:, 1], normals[:, 2], out=north_coefficients, where=valid_edges)
	rounding_margin = 64 * numpy.finfo(float).eps * (numpy.abs(east_coefficients) + numpy.abs(north_coefficients))
	geometry_margin = 1e-8 * (1 + numpy.linalg.norm(edges, axis=1)) / distances
	margins = ANGLE_MARGIN + rounding_margin + geometry_margin
	coverage_starts = starts - margins
	coverage_ends = ends + margins
	first_bins = numpy.floor(coverage_starts / BIN_WIDTH).astype(int)
	last_bins = numpy.floor(coverage_ends / BIN_WIDTH).astype(int)
	counts = last_bins - first_bins + 1
	edge_indices = numpy.repeat(numpy.arange(len(first)), counts)
	bin_indices = numpy.repeat(first_bins, counts) + numpy.arange(counts.sum()) - numpy.repeat(numpy.cumsum(counts) - counts, counts)
	bin_starts = bin_indices * BIN_WIDTH
	bin_ends = bin_starts + BIN_WIDTH
	left = numpy.maximum(bin_starts, coverage_starts[edge_indices])
	right = numpy.minimum(bin_ends, coverage_ends[edge_indices])
	valid = valid_edges[edge_indices]
	east_coefficients = east_coefficients[edge_indices]
	north_coefficients = north_coefficients[edge_indices]
	left_slopes = east_coefficients * numpy.sin(left) + north_coefficients * numpy.cos(left)
	right_slopes = east_coefficients * numpy.sin(right) + north_coefficients * numpy.cos(right)
	maximum_slopes = numpy.maximum(left_slopes, right_slopes)
	minimum_slopes = numpy.minimum(left_slopes, right_slopes)
	peaks = numpy.hypot(east_coefficients, north_coefficients)
	peak_angles = numpy.arctan2(east_coefficients, north_coefficients)
	maximum_inside = (peak_angles - left) % (2 * numpy.pi) <= right - left + ANGLE_MARGIN
	minimum_inside = (peak_angles + numpy.pi - left) % (2 * numpy.pi) <= right - left + ANGLE_MARGIN
	maximum_slopes = numpy.where(maximum_inside, peaks, maximum_slopes)
	minimum_slopes = numpy.where(minimum_inside, -peaks, minimum_slopes)
	maximum_angles = numpy.arctan(maximum_slopes) + margins[edge_indices]
	minimum_angles = numpy.arctan(minimum_slopes) - margins[edge_indices]
	full_bins = (starts[edge_indices] <= bin_starts) & (ends[edge_indices] >= bin_ends) & valid

	if numpy.any(~valid):
		maximum_height = numpy.maximum(first[:, 2], second[:, 2])
		maximum_radius = numpy.maximum(numpy.linalg.norm(first[:, :2], axis=1), numpy.linalg.norm(second[:, :2], axis=1))
		edge_upper = numpy.where(maximum_height >= 0, numpy.pi / 2, numpy.arctan2(maximum_height, maximum_radius))
		maximum_angles = numpy.where(valid, maximum_angles, edge_upper[edge_indices] + margins[edge_indices])

	numpy.maximum.at(upper, bin_indices % HORIZON_BIN_COUNT, maximum_angles)
	numpy.maximum.at(lower, bin_indices[full_bins] % HORIZON_BIN_COUNT, minimum_angles[full_bins])

	return True


class HorizonBuilder:
	def __init__(self, dataset):
		self.surface = TerrainSurface(dataset)
		self.boxes = {}
		self.minimum_radius = dataset.reference_radius + numpy.iinfo(numpy.int16).min * HEIGHT_SCALE
		self.maximum_radius = self.surface.outer_radius

	def box(self, coordinates):
		if coordinates not in self.boxes:
			self.boxes[coordinates] = estimated_box(coordinates, self.minimum_radius, self.maximum_radius)

		return self.boxes[coordinates]

	def update_box(self, coordinates, mesh):
		minimum = mesh.minimum_corner
		maximum = mesh.maximum_corner
		margin = 1e-8 * (1 + numpy.linalg.norm(maximum - minimum))
		self.boxes[coordinates] = minimum - margin, maximum + margin
		face, level, tile_x, tile_y = coordinates

		while level:
			level -= 1
			tile_x //= 2
			tile_y //= 2
			bounds = []

			for child_row in range(2):
				for child_column in range(2):
					child_coordinates = (face, level + 1, tile_x * 2 + child_column, tile_y * 2 + child_row)
					bounds.append(self.box(child_coordinates))

			self.boxes[(face, level, tile_x, tile_y)] = (
				numpy.min([bound[0] for bound in bounds], axis=0),
				numpy.max([bound[1] for bound in bounds], axis=0),
			)

	def build(self, position, normal):
		origin = position + normal * MINIMUM_INTERSECTION_DISTANCE
		basis = local_basis(position)

		segment_count = self.surface.dataset.tile_size - 1
		inner_radius = self.minimum_radius * numpy.sqrt(max(1 / 3, 1 - 2 / segment_count**2))
		baseline = -numpy.arccos(min(1, inner_radius / numpy.linalg.norm(origin)))
		lower = numpy.full(HORIZON_BIN_COUNT, baseline)
		upper = lower.copy()
		pending = []

		for face in range(6):
			heappush(pending, (0.0, (face, 0, 0, 0)))

		while pending:
			_, coordinates = heappop(pending)
			minimum, maximum = self.box(coordinates)
			bins, maximum_elevation = angular_box(minimum, maximum, origin, basis)

			if maximum_elevation < lower[bins].min():
				continue

			face, level, tile_x, tile_y = coordinates

			if f'{face}/{level}/{tile_x}/{tile_y}' in self.surface.refinements:
				for row in range(2):
					for column in range(2):
						child = (face, level + 1, tile_x * 2 + column, tile_y * 2 + row)
						child_minimum, child_maximum = self.box(child)
						nearest = numpy.maximum(child_minimum, numpy.minimum(origin, child_maximum))
						distance = float(numpy.sum((nearest - origin) ** 2))
						heappush(pending, (distance, child))

				continue

			mesh = self.surface.mesh(coordinates)
			self.update_box(coordinates, mesh)
			bins, maximum_elevation = angular_box(*self.boxes[coordinates], origin, basis)

			if maximum_elevation < lower[bins].min():
				continue

			positions = (mesh.positions - origin) @ basis
			first = numpy.concatenate((positions[:, :-1].reshape(-1, 3), positions[:-1, :].reshape(-1, 3), positions[:-1, 1:].reshape(-1, 3)))
			second = numpy.concatenate((positions[:, 1:].reshape(-1, 3), positions[1:, :].reshape(-1, 3), positions[1:, :-1].reshape(-1, 3)))

			if not update_edges(lower, upper, first, second):
				return HorizonProfile.unresolved()

		return HorizonProfile(lower, numpy.maximum(lower, upper))
