import gzip

import numpy
import pytest

from terrain.services.tile_encoding import decode_heights, encode_heights


def test_compact_heights_round_trip_with_at_most_quarter_meter_error():
	heights = numpy.array([[-1000.24, -0.26, 0], [0.26, 1000.24, 11000.1]], dtype=numpy.float32)
	content = encode_heights(heights)
	decoded = decode_heights(content)

	numpy.testing.assert_array_equal(decoded, [-1000, -0.5, 0, 0.5, 1000, 11000])
	assert numpy.max(numpy.abs(decoded - heights.ravel())) <= 0.25
	assert decoded.dtype == numpy.dtype('<f4')
	assert len(gzip.decompress(content)) == heights.size * 2


def test_height_differences_preserve_large_positive_and_negative_transitions():
	heights = numpy.array([-16384, 16383.5, -16384, 16383.5], dtype=numpy.float32)

	decoded = decode_heights(encode_heights(heights))

	numpy.testing.assert_array_equal(decoded, heights)


@pytest.mark.parametrize('height', [numpy.nan, numpy.inf, -numpy.inf, 16384, -16384.5])
def test_invalid_heights_cannot_wrap_or_be_silently_stored(height):
	with pytest.raises(ValueError):
		encode_heights(numpy.array([height], dtype=numpy.float32))


def test_smooth_height_tiles_compress_below_their_integer_payload():
	heights = numpy.arange(65 * 65, dtype=numpy.float32).reshape(65, 65) * 0.5

	content = encode_heights(heights)

	assert len(content) < heights.size * 2
	numpy.testing.assert_array_equal(decode_heights(content), heights.ravel())
