import numpy
import pytest

from terrain.services.body_geometry import body_angles, disk_directions


@pytest.mark.parametrize('sun_vector', [[100.0, 0, 0], [0, 0, 100.0], [0, 0, -100.0]])
def test_solar_samples_cover_the_correct_angular_disk(sun_vector):
	sun_vector = numpy.array(sun_vector)
	directions, angular_radius = disk_directions(sun_vector, 1, 4096)
	center = sun_vector / numpy.linalg.norm(sun_vector)
	angles = numpy.arccos(numpy.clip(directions @ center, -1, 1))

	assert angular_radius == pytest.approx(numpy.arcsin(0.01))
	numpy.testing.assert_allclose(numpy.linalg.norm(directions, axis=1), 1, atol=1e-15)
	assert angles.max() <= angular_radius
	assert angles.max() > angular_radius * 0.99
	numpy.testing.assert_allclose(directions.mean(axis=0), center * numpy.cos(angular_radius / 2) ** 2, atol=1e-5)


def test_a_straight_horizon_through_the_sun_center_leaves_half_the_disk_visible():
	directions, _ = disk_directions(numpy.array([100.0, 0, 0]), 1, 4096)

	assert numpy.mean(directions[:, 2] > 0) == pytest.approx(0.5, abs=0.002)


@pytest.mark.parametrize(
	('direction', 'elevation', 'azimuth'),
	[([0, 0, 1], 0, 0), ([0, 1, 0], 0, 90), ([0, -1, 0], 0, 270), ([1, 0, 0], 90, 0), ([-1, 0, 0], -90, 0)],
)
def test_body_angles_measure_elevation_and_azimuth_clockwise_from_north(direction, elevation, azimuth):
	actual_elevation, actual_azimuth = body_angles(numpy.array([1737400.0, 0, 0]), 0, 0, numpy.array(direction))

	assert actual_elevation == pytest.approx(elevation)
	assert actual_azimuth == pytest.approx(azimuth)
