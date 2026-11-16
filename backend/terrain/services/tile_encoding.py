import gzip

import numpy

HEIGHT_SCALE = 0.5


def encode_heights(heights):
	quantized_heights = numpy.rint(heights / HEIGHT_SCALE)
	integer_limits = numpy.iinfo(numpy.int16)

	if not numpy.isfinite(quantized_heights).all():
		raise ValueError('Terrain tiles must contain finite heights.')

	if (quantized_heights < integer_limits.min).any() or (quantized_heights > integer_limits.max).any():
		raise ValueError('Terrain heights exceed the half-meter Int16 storage range.')

	integer_heights = quantized_heights.astype('<i2').ravel()
	height_differences = numpy.diff(integer_heights, prepend=numpy.int16(0))

	return gzip.compress(height_differences.tobytes(), compresslevel=1, mtime=0)


def decode_heights(content):
	height_differences = numpy.frombuffer(gzip.decompress(content), dtype='<i2')
	integer_heights = numpy.cumsum(height_differences, dtype=numpy.int16)

	return integer_heights.astype('<f4') * HEIGHT_SCALE
