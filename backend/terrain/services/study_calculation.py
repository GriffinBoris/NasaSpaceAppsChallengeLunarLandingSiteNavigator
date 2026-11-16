from django.db import transaction
from django.db.models import F
from ephemeris.services.kernels import kernel_signature
from ephemeris.services.positions import calculate_surface_earths, calculate_surface_suns, loaded_ephemeris

from terrain.models.EarthVisibilityResult import EarthVisibilityResult
from terrain.models.SunlightFrame import SunlightFrame
from terrain.models.SunlightResult import SunlightResult
from terrain.models.SunlightStudy import SunlightStudy
from terrain.services.earth_result_cache import EarthResultCache
from terrain.services.earth_visibility import point_result, region_result
from terrain.services.horizon_storage import load_profiles, save_profile
from terrain.services.illumination_patch import patch_locations, progress_event
from terrain.services.joint_visibility import joint_fractions
from terrain.services.site_combined_visibility import update_combined_visibility
from terrain.services.study_schedule import timestamps
from terrain.services.sunlight_preparation import prepare_selection, restore_selection
from terrain.services.sunlight_processing import SunlightProcessor
from terrain.services.sunlight_result_cache import SunlightResultCache

HORIZON_PREPARATION_THRESHOLD = 256
BODY_LABELS = {'SUN': 'sunlight', 'EARTH': 'Earth visibility'}
CALCULATION_BODIES = ('SUN', 'EARTH')


def study_progress_event(completed_samples, total_samples, stage, phase='calculating'):
	event = progress_event(completed_samples, total_samples, stage)
	event['progress']['phase'] = phase

	return event


def has_result(frame, body):
	if frame is None:
		return False

	if body == 'SUN':
		return frame.visible_sun_fraction is not None

	return frame.cached_earth_result_id is not None


def joint_grid(frame):
	if frame.cached_result_id is None or frame.cached_earth_result_id is None:
		return None

	if frame.cached_result.preparation_id != frame.cached_earth_result.preparation_id:
		return None

	if frame.cached_result.ephemeris_signature != frame.cached_earth_result.ephemeris_signature:
		return None

	return joint_fractions(frame.cached_result.result, frame.cached_earth_result.result)


@transaction.atomic
def save_frame(study, selection, result, body):
	frame, _ = SunlightFrame.objects.get_or_create(study=study, selection_id=selection['id'], timestamp=result.timestamp)
	previous_grid = frame.joint_grid

	if body == 'SUN':
		frame.cached_result = result
		frame.visible_sun_fraction = result.visible_sun_fraction
		frame.thumbnail = result.thumbnail
		frame.result = None
	else:
		frame.cached_earth_result = result
		frame.visible_earth_fraction = result.visible_earth_fraction
		frame.earth_center_visible = result.earth_center_visible

	frame.joint_grid = joint_grid(frame)
	frame.joint_visible_share = None

	if frame.joint_grid is not None:
		samples = [fraction for fraction in frame.joint_grid if fraction is not None]
		frame.joint_visible_share = sum(samples) / len(samples)

	SunlightStudy.objects.filter(pk=study.pk).update(result_revision=F('result_revision') + 1)
	frame.result_revision = SunlightStudy.objects.values_list('result_revision', flat=True).get(pk=study.pk)
	frame.save()

	if selection['radius_meters'] is not None:
		update_combined_visibility(study, frame, previous_grid)

	return frame


def preparation_events(study, selection, processor, horizon_contents, build_missing):
	total_profiles = sum(content is not None or build_missing for content in horizon_contents)
	completed_profiles = 0

	for index, content in processor.prepare_profiles(horizon_contents, build_missing=build_missing):
		if index is not None:
			completed_profiles += 1

			if content is not None:
				save_profile(study.dataset, processor.locations[index], content)

		stage = f'{selection["name"]}: starting calculation workers'

		if total_profiles:
			stage = f'{selection["name"]}: preparing remaining terrain and horizons, {completed_profiles} of {total_profiles}'

		yield study_progress_event(completed_profiles, total_profiles or 1, stage, phase='preparing')


def iter_study(study):
	schedule = timestamps(study.start_time, study.end_time, study.step_seconds)
	stored_frames = {}

	for frame in study.frames.defer('result', 'thumbnail'):
		stored_frames[(frame.selection_id, frame.timestamp)] = frame

	samples_per_selection = {}

	for selection in study.selections:
		sample_count = 1

		if selection['radius_meters'] is not None:
			locations = patch_locations(selection['latitude'], selection['longitude'], selection['radius_meters'], study.dataset.reference_radius)
			sample_count = sum(location is not None for location in locations) + 1

		samples_per_selection[selection['id']] = sample_count

	total_samples = len(schedule) * sum(samples_per_selection.values()) * len(CALCULATION_BODIES)
	completed_samples = 0

	for frame in stored_frames.values():
		for body in CALCULATION_BODIES:
			if has_result(frame, body):
				completed_samples += samples_per_selection[frame.selection_id]

	yield study_progress_event(0, 1, 'Preparing saved selections', phase='preparing')

	for timestamp in (schedule[0], schedule[-1]):
		with loaded_ephemeris(timestamp):
			pass

	ephemeris_signature = kernel_signature()

	for selection in study.selections:
		remaining_timestamps = {}

		for body in CALCULATION_BODIES:
			missing_timestamps = []

			for timestamp in schedule:
				frame = stored_frames.get((selection['id'], timestamp))

				if not has_result(frame, body):
					missing_timestamps.append(timestamp)

			remaining_timestamps[body] = missing_timestamps

		if not any(remaining_timestamps.values()):
			continue

		yield study_progress_event(0, 1, f'{selection["name"]}: reading terrain samples', phase='preparing')

		preparation = prepare_selection(study.dataset, selection)
		result_caches = {
			'SUN': SunlightResultCache(preparation, ephemeris_signature),
			'EARTH': EarthResultCache(preparation, ephemeris_signature),
		}

		for body in CALCULATION_BODIES:
			cached_result_ids = result_caches[body].result_ids(study.start_time, study.end_time)
			result_model = SunlightResult if body == 'SUN' else EarthVisibilityResult

			for timestamp in remaining_timestamps[body]:
				if timestamp not in cached_result_ids:
					continue

				result = result_model.objects.get(pk=cached_result_ids[timestamp])
				save_frame(study, selection, result, body)
				completed_samples += samples_per_selection[selection['id']]

				yield study_progress_event(
					completed_samples, total_samples, f'{selection["name"]}, {timestamp:%Y-%m-%d %H:%M} UTC: reused saved {BODY_LABELS[body]}'
				)

			missing_timestamps = []

			for timestamp in remaining_timestamps[body]:
				if timestamp not in cached_result_ids:
					missing_timestamps.append(timestamp)

			remaining_timestamps[body] = missing_timestamps

		if not any(remaining_timestamps.values()):
			continue

		for body in CALCULATION_BODIES:
			remaining_timestamps[body] = set(remaining_timestamps[body])

		sample_points, region = restore_selection(preparation)
		locations = [(point.latitude, point.longitude) for point in sample_points]
		surface_positions = [point.position for point in sample_points]
		sample_geometry = [point.geometry() for point in sample_points]
		horizon_contents = load_profiles(study.dataset, locations)
		build_missing = len(schedule) >= HORIZON_PREPARATION_THRESHOLD and any(content is None for content in horizon_contents)

		with SunlightProcessor(study.dataset_id, locations, workers=study.worker_count, geometry=sample_geometry) as processor:
			yield from preparation_events(study, selection, processor, horizon_contents, build_missing=False)
			first_result_saved = False

			for timestamp in schedule:
				if not any(timestamp in remaining_timestamps[body] for body in CALCULATION_BODIES):
					continue

				if build_missing and first_result_saved:
					yield from preparation_events(study, selection, processor, horizon_contents, build_missing=True)
					build_missing = False

				for body in CALCULATION_BODIES:
					if timestamp not in remaining_timestamps[body]:
						continue

					label = f'{selection["name"]}, {timestamp:%Y-%m-%d %H:%M} UTC'
					body_label = BODY_LABELS[body]
					position_function = calculate_surface_suns
					body_name = 'the Sun'

					if body == 'EARTH':
						position_function = calculate_surface_earths
						body_name = 'Earth'

					yield study_progress_event(completed_samples, total_samples, f'{label}: locating {body_name}')
					body_vectors, body_radius = position_function(timestamp, surface_positions)

					for calculation_update in processor.calculate(body_vectors, body_radius, body):
						calculated_samples, _ = calculation_update
						yield study_progress_event(completed_samples + calculated_samples, total_samples, f'{label}: tracing {body_label}')

					_, visibilities = calculation_update
					patch_result = None

					if body == 'SUN':
						if region is None:
							center_result = sample_points[0].result(timestamp, body_vectors[0], visibilities[0])
						else:
							patch_result = region.result(timestamp, body_vectors, visibilities)
							center_result = patch_result['center']
					elif region is None:
						center_result = point_result(sample_points[0], timestamp, body_vectors[0], visibilities[0])
					else:
						patch_result = region_result(region, timestamp, body_vectors, visibilities)
						center_result = patch_result['center']

					result = result_caches[body].store(timestamp, center_result, patch_result)
					save_frame(study, selection, result, body)
					completed_samples += samples_per_selection[selection['id']]

					yield study_progress_event(completed_samples, total_samples, f'{label}: saved {body_label}')

				first_result_saved = True

	yield {'type': 'result', 'result': {'study_id': study.pk}}
