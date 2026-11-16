import numpy

from terrain.services.tile_grid import cube_coordinates


def surface_direction(latitude, longitude):
	latitude = numpy.radians(latitude)
	longitude = numpy.radians(longitude)

	return numpy.array([numpy.cos(latitude) * numpy.cos(longitude), numpy.cos(latitude) * numpy.sin(longitude), numpy.sin(latitude)])


def cube_surface_directions(face, horizontal, vertical):
	coordinate_x, coordinate_y, coordinate_z = cube_coordinates(face, horizontal, vertical)
	directions = numpy.stack((coordinate_x, -coordinate_z, coordinate_y), axis=-1)

	return directions / numpy.linalg.norm(directions, axis=-1, keepdims=True)


def face_coordinates(direction):
	coordinate_x, coordinate_y, coordinate_z = direction
	major_axis = numpy.argmax(numpy.abs(direction))

	if major_axis == 0:
		if coordinate_x > 0:
			return 0, coordinate_y / coordinate_x, coordinate_z / coordinate_x

		return 1, coordinate_y / coordinate_x, -coordinate_z / coordinate_x

	if major_axis == 2:
		if coordinate_z > 0:
			return 2, coordinate_x / coordinate_z, coordinate_y / coordinate_z

		return 3, -coordinate_x / coordinate_z, coordinate_y / coordinate_z

	if coordinate_y < 0:
		return 4, -coordinate_x / coordinate_y, -coordinate_z / coordinate_y

	return 5, -coordinate_x / coordinate_y, coordinate_z / coordinate_y


def tile_bounds(level, tile_x, tile_y):
	divisions = 2**level
	left = -1 + 2 * tile_x / divisions
	right = -1 + 2 * (tile_x + 1) / divisions
	top = 1 - 2 * tile_y / divisions
	bottom = 1 - 2 * (tile_y + 1) / divisions

	return left, right, top, bottom


def rays_cross_tile(origin, directions, coordinates, maximum_distances):
	face, level, tile_x, tile_y = coordinates
	left, right, top, bottom = tile_bounds(level, tile_x, tile_y)
	corners = cube_surface_directions(face, numpy.array([left, right, right, left]), numpy.array([top, top, bottom, bottom]))
	center = corners.sum(axis=0)
	plane_normals = numpy.cross(corners, numpy.roll(corners, -1, axis=0))
	plane_normals *= numpy.sign(plane_normals @ center)[:, None]

	minimum_distances = numpy.zeros(len(directions))
	maximum_distances = maximum_distances.copy()

	for normal in plane_normals:
		origin_distance = origin @ normal
		rates = directions @ normal
		crossings = numpy.zeros(len(directions))

		numpy.divide(-origin_distance, rates, out=crossings, where=rates != 0)
		minimum_distances = numpy.where(rates > 0, numpy.maximum(minimum_distances, crossings), minimum_distances)
		maximum_distances = numpy.where(rates < 0, numpy.minimum(maximum_distances, crossings), maximum_distances)
		maximum_distances = numpy.where((rates == 0) & (origin_distance < -1e-9), -1, maximum_distances)

	return maximum_distances >= minimum_distances
