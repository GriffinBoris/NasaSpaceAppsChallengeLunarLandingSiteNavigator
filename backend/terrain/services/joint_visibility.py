from terrain.services.disk_visibility import VISIBLE_FRACTION_TOLERANCE


def joint_fractions(sunlight, earth):
	sunlight_points = sunlight['patch']['points'] if sunlight['patch'] is not None else [sunlight['center']]
	earth_points = earth['patch']['points'] if earth['patch'] is not None else [earth['center']]
	fractions = []

	for sunlight_point, earth_point in zip(sunlight_points, earth_points, strict=True):
		if sunlight_point is None:
			fractions.append(None)
			continue

		is_visible = sunlight_point['visible_sun_fraction'] > VISIBLE_FRACTION_TOLERANCE and earth_point['earth_center_visible']
		fractions.append(int(is_visible))

	return fractions
