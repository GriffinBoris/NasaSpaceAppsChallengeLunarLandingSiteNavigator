from datetime import UTC, datetime

from ephemeris.views.positions.serializers import EphemerisOutputSerializer, EphemerisQuerySerializer


class TestEphemerisQuerySerializer:
	def test_timestamp_offset_is_normalized_to_utc(self):
		serializer = EphemerisQuerySerializer(data={'timestamp': '2026-11-11T07:00:00-05:00'})
		assert serializer.is_valid(), serializer.errors
		assert serializer.validated_data == {'timestamp': datetime(2026, 11, 11, 12, tzinfo=UTC)}

	def test_timestamp_is_required(self):
		serializer = EphemerisQuerySerializer(data={})
		assert not serializer.is_valid()
		assert serializer.errors == {'timestamp': ['This field is required.']}


class TestEphemerisOutputSerializer:
	def test_body_vectors_and_utc_time_have_an_exact_public_shape(self):
		result = {
			'timestamp': datetime(2026, 11, 11, 12, tzinfo=UTC),
			'frame': 'MOON_ME_DE421',
			'sun': {'position_km': [100, 200, 300], 'radius_km': 695700},
			'earth': {'position_km': [400, 500, 600], 'radius_km': 6371},
		}
		data = dict(EphemerisOutputSerializer(result).data)
		assert data.pop('timestamp') == '2026-11-11T12:00:00Z'
		assert data.pop('frame') == 'MOON_ME_DE421'
		assert data.pop('sun') == {'position_km': [100, 200, 300], 'radius_km': 695700}
		assert data.pop('earth') == {'position_km': [400, 500, 600], 'radius_km': 6371}
		assert not data
