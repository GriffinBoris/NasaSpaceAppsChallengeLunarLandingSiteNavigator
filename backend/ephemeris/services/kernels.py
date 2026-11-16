from hashlib import file_digest, sha256

import spiceypy
from django.conf import settings

KERNEL_URLS = (
	'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/naif0012.tls',
	'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/a_old_versions/de421.bsp',
	'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/fk/satellites/moon_080317.tf',
	'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/moon_pa_de421_1900-2050.bpc',
	'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/pck00011.tpc',
)


def kernel_paths():
	return [settings.SPICE_ROOT / source_url.rsplit('/', 1)[1] for source_url in KERNEL_URLS]


def kernel_signature():
	digest = sha256(spiceypy.__version__.encode())

	for path in kernel_paths():
		with path.open('rb') as kernel_file:
			digest.update(path.name.encode())
			digest.update(file_digest(kernel_file, 'sha256').digest())

	return digest.hexdigest()
