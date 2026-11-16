from rest_framework.exceptions import APIException


class EphemerisServiceUnavailable(APIException):
	status_code = 503
	default_code = 'ephemeris_unavailable'
