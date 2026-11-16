from terrain.models.SunlightResult import SunlightResult
from terrain.services.visibility_summary import summarize_visibility

CALCULATION_VERSION = 1


class SunlightResultCache:
	def __init__(self, preparation, ephemeris_signature):
		self.identity = {
			'preparation': preparation,
			'version': CALCULATION_VERSION,
			'ephemeris_signature': ephemeris_signature,
		}

	def result_ids(self, start_time, end_time):
		rows = SunlightResult.objects.filter(**self.identity, timestamp__gte=start_time, timestamp__lt=end_time).values_list('timestamp', 'id')

		return dict(rows)

	def store(self, timestamp, center, patch):
		center['timestamp'] = timestamp.isoformat().replace('+00:00', 'Z')
		visible_fraction, thumbnail = summarize_visibility(center, patch, 'visible_sun_fraction')

		result, _ = SunlightResult.objects.get_or_create(
			**self.identity,
			timestamp=timestamp,
			defaults={'visible_sun_fraction': visible_fraction, 'thumbnail': thumbnail, 'result': {'center': center, 'patch': patch}},
		)

		return result
