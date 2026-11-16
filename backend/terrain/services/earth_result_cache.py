from terrain.models.EarthVisibilityResult import EarthVisibilityResult
from terrain.services.visibility_summary import summarize_visibility

EARTH_CALCULATION_VERSION = 1


class EarthResultCache:
	def __init__(self, preparation, ephemeris_signature):
		self.identity = {
			'preparation': preparation,
			'version': EARTH_CALCULATION_VERSION,
			'ephemeris_signature': ephemeris_signature,
		}

	def result_ids(self, start_time, end_time):
		rows = EarthVisibilityResult.objects.filter(**self.identity, timestamp__gte=start_time, timestamp__lt=end_time).values_list('timestamp', 'id')

		return dict(rows)

	def store(self, timestamp, center, patch):
		center['timestamp'] = timestamp.isoformat().replace('+00:00', 'Z')
		visible_fraction, thumbnail = summarize_visibility(center, patch, 'visible_earth_fraction')

		result, _ = EarthVisibilityResult.objects.get_or_create(
			**self.identity,
			timestamp=timestamp,
			defaults={
				'visible_earth_fraction': visible_fraction,
				'earth_center_visible': center['earth_center_visible'],
				'thumbnail': thumbnail,
				'result': {'center': center, 'patch': patch},
			},
		)

		return result
