from math import ceil

from django.db import transaction

from terrain.models.StudyCombinedVisibility import StudyCombinedVisibility
from terrain.services.study_results import result_changes
from terrain.services.terrain_surface import TerrainAnalysisUnavailable


def accumulate_grid(combined_visibility, joint_grid, duration_seconds, contribution_sign):
	for sample_index, visible_fraction in enumerate(joint_grid):
		if visible_fraction is None:
			continue

		combined_visibility.visible_seconds[sample_index] += contribution_sign * visible_fraction * duration_seconds

	combined_visibility.checked_frames += contribution_sign
	combined_visibility.checked_seconds += contribution_sign * duration_seconds


def update_combined_visibility(study, frame, previous_joint_grid):
	if previous_joint_grid is None and frame.joint_grid is None:
		return

	sunlight_result = frame.cached_result
	joint_grid = frame.joint_grid

	if joint_grid is None:
		joint_grid = previous_joint_grid

	combined_visibility, _ = StudyCombinedVisibility.objects.get_or_create(
		study=study,
		selection_id=frame.selection_id,
		defaults={
			'preparation_id': sunlight_result.preparation_id,
			'ephemeris_signature': sunlight_result.ephemeris_signature,
			'visible_seconds': [None if fraction is None else 0 for fraction in joint_grid],
		},
	)

	if (
		combined_visibility.preparation_id != sunlight_result.preparation_id
		or combined_visibility.ephemeris_signature != sunlight_result.ephemeris_signature
	):
		raise TerrainAnalysisUnavailable('Saved results use different terrain preparations or ephemerides. Compare them in separate plans.')

	if previous_joint_grid == frame.joint_grid:
		return

	duration_seconds = min(study.step_seconds, (study.end_time - frame.timestamp).total_seconds())

	if previous_joint_grid is not None:
		accumulate_grid(combined_visibility, previous_joint_grid, duration_seconds, -1)

	if frame.joint_grid is not None:
		accumulate_grid(combined_visibility, frame.joint_grid, duration_seconds, 1)

	combined_visibility.save()


@transaction.atomic
def rebuild_combined_visibility(study):
	study.combined_visibility.all().delete()
	region_ids = []

	for selection in study.selections:
		if selection['radius_meters'] is not None:
			region_ids.append(selection['id'])

	frames = study.frames.filter(selection_id__in=region_ids, joint_grid__isnull=False).select_related('cached_result')
	frames = frames.defer('result', 'thumbnail', 'cached_result__result', 'cached_result__thumbnail')
	combined_visibility_by_selection = {}

	for frame in frames.iterator(chunk_size=32):
		sunlight_result = frame.cached_result

		if frame.selection_id not in combined_visibility_by_selection:
			combined_visibility_by_selection[frame.selection_id] = StudyCombinedVisibility(
				study=study,
				selection_id=frame.selection_id,
				preparation_id=sunlight_result.preparation_id,
				ephemeris_signature=sunlight_result.ephemeris_signature,
				visible_seconds=[None if fraction is None else 0 for fraction in frame.joint_grid],
			)

		combined_visibility = combined_visibility_by_selection[frame.selection_id]

		if (
			sunlight_result.preparation_id != combined_visibility.preparation_id
			or sunlight_result.ephemeris_signature != combined_visibility.ephemeris_signature
		):
			raise TerrainAnalysisUnavailable('Saved results use different terrain preparations or ephemerides. Compare them in separate plans.')

		duration_seconds = min(study.step_seconds, (study.end_time - frame.timestamp).total_seconds())
		accumulate_grid(combined_visibility, frame.joint_grid, duration_seconds, 1)

	StudyCombinedVisibility.objects.bulk_create(combined_visibility_by_selection.values())


def site_combined_visibility(study, selection, after_revision=None):
	if selection['radius_meters'] is None:
		raise TerrainAnalysisUnavailable('Choose a region to compare areas within a site.')

	total_seconds = (study.end_time - study.start_time).total_seconds()
	frames, reset_history = result_changes(study, after_revision)
	response = {
		'selection_id': selection['id'],
		'result_revision': study.result_revision,
		'reset': reset_history,
		'total_seconds': total_seconds,
		'checked_seconds': 0,
		'checked_frames': 0,
		'expected_frames': ceil(total_seconds / study.step_seconds),
		'grid': None,
		'previews': [],
	}
	combined_visibility = study.combined_visibility.filter(selection_id=selection['id']).select_related('preparation').first()

	if combined_visibility is None:
		if study.frames.filter(selection_id=selection['id'], joint_visible_share__isnull=False).exists():
			raise TerrainAnalysisUnavailable('Prepare the combined map for this saved plan before viewing it.')

		return response

	preparation = combined_visibility.preparation
	grid_size = preparation.grid_size
	samples = []

	for sample, visible_seconds in zip(preparation.samples, combined_visibility.visible_seconds, strict=True):
		if sample is None:
			samples.append(None)
			continue

		samples.append({'latitude': sample['latitude'], 'longitude': sample['longitude'], 'visible_seconds': visible_seconds})

	response['checked_seconds'] = combined_visibility.checked_seconds
	response['checked_frames'] = combined_visibility.checked_frames
	response['grid'] = {
		'grid_size': grid_size,
		'radius_meters': preparation.radius_meters,
		'spacing_meters': 2 * preparation.radius_meters / (grid_size - 1),
		'samples': samples,
	}
	preview_grid_size = len(range(0, grid_size, 2))
	frames = frames.filter(selection_id=selection['id'], joint_grid__isnull=False).values('id', 'joint_grid')

	for frame in frames:
		visible_fractions = []

		for row_index in range(0, grid_size, 2):
			for column_index in range(0, grid_size, 2):
				sample_index = row_index * grid_size + column_index
				visible_fractions.append(frame['joint_grid'][sample_index])

		response['previews'].append({'frame_id': frame['id'], 'grid_size': preview_grid_size, 'fractions': visible_fractions})

	return response
