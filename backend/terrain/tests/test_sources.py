import pytest

from terrain.services.sources import PRESETS, global_source_filenames


@pytest.mark.parametrize('resolution,level,count', [('4', 2, 1), ('16', 4, 1), ('64', 6, 1), ('128', 7, 1), ('256', 8, 4), ('512', 9, 16)])
def test_numeric_resolution_has_matching_sources_and_detail_limit(resolution, level, count):
	preset = PRESETS[resolution]
	filenames = global_source_filenames(preset.pixels_per_degree)

	assert preset.global_level == level
	assert len(set(filenames)) == count
	assert all(filename.startswith(f'LDEM_{resolution}') for filename in filenames)


def test_tiled_source_filenames_match_the_nasa_archive():
	assert global_source_filenames(256) == [
		'LDEM_256_00N_90N_000_180',
		'LDEM_256_00N_90N_180_360',
		'LDEM_256_90S_00S_000_180',
		'LDEM_256_90S_00S_180_360',
	]
	assert 'LDEM_512_90S_45S_270_360' in global_source_filenames(512)
	assert 'LDEM_512_45N_90N_000_090' in global_source_filenames(512)
