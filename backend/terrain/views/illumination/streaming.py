import json
import logging

from ephemeris.services.positions import EphemerisTimeError, EphemerisUnavailable

from terrain.services.terrain_surface import TerrainAnalysisUnavailable

logger = logging.getLogger(__name__)


def stream_illumination(events, result_serializer):
	try:
		for event in events:
			if event['type'] == 'result':
				event = {'type': 'result', 'result': result_serializer(event['result']).data}

			yield json.dumps(event, allow_nan=False) + '\n'
	except (EphemerisTimeError, EphemerisUnavailable, TerrainAnalysisUnavailable) as error:
		logger.warning('Visibility calculation unavailable', exc_info=True)
		yield json.dumps({'type': 'error', 'message': str(error)}) + '\n'
	except Exception:
		logger.exception('Visibility calculation failed')
		yield json.dumps({'type': 'error', 'message': 'Unable to calculate visibility. Please try again.'}) + '\n'
	finally:
		events.close()
