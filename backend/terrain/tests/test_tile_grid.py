import numpy
import pytest

from terrain.services.tile_grid import tile_coordinates


@pytest.mark.parametrize('face,longitude,latitude', [(0, 0, 0), (1, 180, 0), (2, 0, 90), (3, 0, -90), (4, 270, 0), (5, 90, 0)])
def test_face_centers_match_lunar_axes(face, longitude, latitude):
	longitudes, latitudes = tile_coordinates(face, 0, 0, 0, 5)

	assert latitudes[2, 2] == latitude
	if abs(latitude) != 90:
		assert longitudes[2, 2] == longitude


def test_neighboring_cube_faces_share_geographic_edges():
	first_longitudes, first_latitudes = tile_coordinates(0, 0, 0, 0, 5)
	second_longitudes, second_latitudes = tile_coordinates(5, 0, 0, 0, 5)

	numpy.testing.assert_array_equal(first_longitudes[:, -1], second_longitudes[:, 0])
	numpy.testing.assert_array_equal(first_latitudes[:, -1], second_latitudes[:, 0])
