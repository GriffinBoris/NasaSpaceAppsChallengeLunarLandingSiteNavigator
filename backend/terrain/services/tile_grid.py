import numpy

REFERENCE_RADIUS = 1737400.0


def cube_coordinates(face, horizontal, vertical):
	unit_values = numpy.ones_like(horizontal)

	if face == 0:
		return unit_values, vertical, -horizontal
	if face == 1:
		return -unit_values, vertical, horizontal
	if face == 2:
		return horizontal, unit_values, -vertical
	if face == 3:
		return horizontal, -unit_values, vertical
	if face == 4:
		return horizontal, vertical, unit_values

	return -horizontal, vertical, -unit_values


def tile_coordinates(face, level, tile_x, tile_y, tile_size):
	divisions = 2**level
	horizontal = numpy.linspace(-1 + 2 * tile_x / divisions, -1 + 2 * (tile_x + 1) / divisions, tile_size)
	vertical = numpy.linspace(1 - 2 * tile_y / divisions, 1 - 2 * (tile_y + 1) / divisions, tile_size)
	horizontal, vertical = numpy.meshgrid(horizontal, vertical)
	coordinate_x, coordinate_y, coordinate_z = cube_coordinates(face, horizontal, vertical)
	coordinate_length = numpy.sqrt(coordinate_x * coordinate_x + coordinate_y * coordinate_y + coordinate_z * coordinate_z)

	latitudes = numpy.degrees(numpy.arcsin(coordinate_y / coordinate_length))
	longitudes = numpy.degrees(numpy.arctan2(-coordinate_z, coordinate_x)) % 360

	return longitudes, latitudes
