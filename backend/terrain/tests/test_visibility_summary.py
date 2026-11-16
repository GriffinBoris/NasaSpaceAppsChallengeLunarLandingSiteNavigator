import pytest

from terrain.services.visibility_summary import summarize_visibility


@pytest.mark.parametrize('fraction_field', ['visible_sun_fraction', 'visible_earth_fraction'])
def test_region_summary_excludes_exterior_samples_and_preserves_thumbnail_positions(fraction_field):
	values = [None, 0.2, 0.4, 0.6, 0.8, 0, 0.2, 0.4, None]
	patch = {'grid_size': 3, 'points': [None if value is None else {fraction_field: value} for value in values]}

	average, thumbnail = summarize_visibility({fraction_field: 0.8}, patch, fraction_field)

	assert average == pytest.approx(2.6 / 7)
	assert thumbnail == {'grid_size': 2, 'fractions': [None, 0.4, 0.2, None]}


def test_point_summary_uses_the_center_without_a_thumbnail():
	assert summarize_visibility({'visible_sun_fraction': 0.75}, None, 'visible_sun_fraction') == (0.75, None)
