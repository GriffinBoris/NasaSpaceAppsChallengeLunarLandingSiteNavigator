import gzip

import numpy

HORIZON_VERSION = 1
HORIZON_BIN_COUNT = 4096
ANGLE_MARGIN = 1e-9


def local_basis(position):
	up = position / numpy.linalg.norm(position)
	east = numpy.cross([0.0, 0, 1], up)

	if numpy.linalg.norm(east) < 1e-12:
		east = numpy.array([0.0, 1, 0])

	east /= numpy.linalg.norm(east)
	north = numpy.cross(up, east)

	return numpy.column_stack((east, north, up))


class HorizonProfile:
	def __init__(self, lower, upper):
		self.lower = lower
		self.upper = upper

	@classmethod
	def unresolved(cls):
		return cls(numpy.full(HORIZON_BIN_COUNT, -numpy.pi / 2), numpy.full(HORIZON_BIN_COUNT, numpy.pi / 2))

	def classify(self, directions, basis):
		local_directions = directions @ basis
		azimuths = numpy.arctan2(local_directions[:, 0], local_directions[:, 1]) % (2 * numpy.pi)
		indices = numpy.floor(azimuths * HORIZON_BIN_COUNT / (2 * numpy.pi)).astype(int) % HORIZON_BIN_COUNT
		elevations = numpy.arctan2(local_directions[:, 2], numpy.linalg.norm(local_directions[:, :2], axis=1))
		blocked = elevations < self.lower[indices] - ANGLE_MARGIN
		clear = elevations > self.upper[indices] + ANGLE_MARGIN

		return blocked, ~(blocked | clear)

	def encode(self):
		bounds = numpy.stack((self.lower, self.upper)).astype('<f8')

		return gzip.compress(bounds.tobytes(), mtime=0)

	@classmethod
	def decode(cls, content):
		bounds = numpy.frombuffer(gzip.decompress(content), dtype='<f8').reshape(2, HORIZON_BIN_COUNT)

		return cls(bounds[0], bounds[1])
