import numpy


def disk_directions(body_vector, body_radius, sample_count):
	distance = numpy.linalg.norm(body_vector)
	center_direction = body_vector / distance
	angular_radius = numpy.arcsin(body_radius / distance)
	reference_axis = numpy.array([0.0, 0.0, 1.0])

	if abs(center_direction[2]) > 0.9:
		reference_axis = numpy.array([1.0, 0.0, 0.0])

	horizontal_axis = numpy.cross(center_direction, reference_axis)
	horizontal_axis /= numpy.linalg.norm(horizontal_axis)
	vertical_axis = numpy.cross(center_direction, horizontal_axis)

	sample_indices = numpy.arange(sample_count)
	azimuths = sample_indices * numpy.pi * (3 - numpy.sqrt(5))
	cosine_angles = 1 - (sample_indices + 0.5) / sample_count * (1 - numpy.cos(angular_radius))
	sine_angles = numpy.sqrt(1 - cosine_angles**2)

	directions = cosine_angles[:, None] * center_direction
	directions += (sine_angles * numpy.cos(azimuths))[:, None] * horizontal_axis
	directions += (sine_angles * numpy.sin(azimuths))[:, None] * vertical_axis

	return directions, angular_radius


def body_angles(position, latitude, longitude, body_direction):
	up = position / numpy.linalg.norm(position)
	longitude_radians = numpy.radians(longitude)
	latitude_radians = numpy.radians(latitude)
	east = numpy.array([-numpy.sin(longitude_radians), numpy.cos(longitude_radians), 0])
	north = numpy.array(
		[
			-numpy.sin(latitude_radians) * numpy.cos(longitude_radians),
			-numpy.sin(latitude_radians) * numpy.sin(longitude_radians),
			numpy.cos(latitude_radians),
		]
	)

	elevation = numpy.degrees(numpy.arcsin(numpy.clip(body_direction @ up, -1, 1)))
	azimuth = numpy.degrees(numpy.arctan2(body_direction @ east, body_direction @ north)) % 360

	return float(elevation), float(azimuth)
