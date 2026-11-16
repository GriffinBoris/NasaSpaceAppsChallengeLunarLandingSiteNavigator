def summarize_visibility(center, patch, fraction_field):
	if patch is None:
		return center[fraction_field], None

	points = patch['points']
	fractions = [point[fraction_field] for point in points if point is not None]
	grid_size = patch['grid_size']
	thumbnail_fractions = []

	for row in range(0, grid_size, 2):
		for column in range(0, grid_size, 2):
			point = points[row * grid_size + column]
			thumbnail_fractions.append(None if point is None else point[fraction_field])

	thumbnail = {'grid_size': len(range(0, grid_size, 2)), 'fractions': thumbnail_fractions}

	return sum(fractions) / len(fractions), thumbnail
