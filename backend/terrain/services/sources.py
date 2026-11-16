from dataclasses import dataclass

GLOBAL_SOURCE_URL = 'https://imbrium.mit.edu/DATA/LOLA_GDR/CYLINDRICAL/IMG'
SOUTH_POLE_URL = 'https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_80MPP_ADJ.TIF'


@dataclass(frozen=True)
class TerrainPreset:
	pixels_per_degree: int
	global_level: int
	south_pole: bool = False


PRESETS = {
	'4': TerrainPreset(4, 2),
	'16': TerrainPreset(16, 4),
	'64': TerrainPreset(64, 6),
	'128': TerrainPreset(128, 7),
	'256': TerrainPreset(256, 8),
	'512': TerrainPreset(512, 9),
	'south-pole': TerrainPreset(16, 4, south_pole=True),
}


def global_source_filenames(pixels_per_degree):
	if pixels_per_degree <= 128:
		return [f'LDEM_{pixels_per_degree}']

	if pixels_per_degree == 256:
		latitude_ranges = ('00N_90N', '90S_00S')
		longitude_step = 180
	else:
		latitude_ranges = ('00N_45N', '45N_90N', '45S_00S', '90S_45S')
		longitude_step = 90

	filenames = []

	for latitude_range in latitude_ranges:
		for longitude_start in range(0, 360, longitude_step):
			longitude_end = longitude_start + longitude_step
			filenames.append(f'LDEM_{pixels_per_degree}_{latitude_range}_{longitude_start:03}_{longitude_end:03}')

	return filenames
