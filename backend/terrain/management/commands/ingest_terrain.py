from contextlib import ExitStack

from core.management.progress import Progress
from core.services.downloads import download_file
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from rasterio.errors import RasterioError

from terrain.services.ingestion import TerrainIngestion
from terrain.services.mosaic import build_mosaic
from terrain.services.raster import TerrainRaster
from terrain.services.sources import GLOBAL_SOURCE_URL, PRESETS, SOUTH_POLE_URL, global_source_filenames


class Command(BaseCommand):
	help = 'Download LOLA terrain and store compact tile rows in the database. Defaults to 512 pixels per degree.'

	def add_arguments(self, parser):
		parser.add_argument('resolution', nargs='?', choices=PRESETS, default='512')
		parser.add_argument('--workers', type=int, choices=range(2, 9), default=2, help='Number of terrain sampling processes (default: 2).')
		parser.add_argument('--delete-sources', action='store_true', help='Remove downloaded inputs after a successful import.')

	def handle(self, **options):
		terrain_preset = PRESETS[options['resolution']]
		self.source_paths = set()

		try:
			global_label_path, global_source_url = self._download_global(terrain_preset.pixels_per_degree)
			self.stdout.write('Reading global terrain sources...')

			with ExitStack() as resources:
				global_raster = resources.enter_context(TerrainRaster(global_label_path, global_source_url, is_global=True))
				south_pole_raster = None

				if terrain_preset.south_pole:
					south_pole_path = self._download(SOUTH_POLE_URL)
					south_pole_raster = resources.enter_context(TerrainRaster(south_pole_path, SOUTH_POLE_URL, is_global=False))

				self.stdout.write('Planning terrain tiles...')

				ingestion = TerrainIngestion(global_raster, south_pole_raster, global_level=terrain_preset.global_level)
				progress = Progress(self.stdout, 'Loading terrain')

				self.stdout.write(f'Processing with {options["workers"]} workers and one database writer...')
				dataset = ingestion.run('moon', on_progress=progress.update, workers=options['workers'])
		except (OSError, ValueError, RasterioError) as error:
			raise CommandError(str(error)) from error

		if options['delete_sources']:
			self.stdout.write('Removing downloaded terrain sources...')

			try:
				for source_path in sorted(self.source_paths):
					source_path.unlink()
			except OSError as error:
				raise CommandError(f'Terrain was published, but downloaded sources could not be removed: {error}') from error

		self.stdout.write(self.style.SUCCESS(f'Loaded {dataset.tile_count} tiles ({options["resolution"]}).'))
		self.stdout.write(f'Compressed terrain payload: {ingestion.stored_bytes / 1_000_000_000:.3f} GB, excluding database and index overhead.')

	def _download_global(self, pixels_per_degree):
		label_paths = []
		filenames = global_source_filenames(pixels_per_degree)

		for filename in filenames:
			label_paths.append(self._download(f'{GLOBAL_SOURCE_URL}/{filename}.LBL'))
			self._download(f'{GLOBAL_SOURCE_URL}/{filename}.IMG')

		if len(label_paths) == 1:
			return label_paths[0], f'{GLOBAL_SOURCE_URL}/{filenames[0]}.IMG'

		self.stdout.write('Preparing global mosaic...')

		mosaic_path = settings.MEDIA_ROOT / 'sources' / 'retained' / f'LDEM_{pixels_per_degree}.vrt'
		build_mosaic(label_paths, mosaic_path)
		self.source_paths.add(mosaic_path)

		return mosaic_path, GLOBAL_SOURCE_URL

	def _download(self, source_url):
		source_filename = source_url.rsplit('/', 1)[1]
		progress = Progress(self.stdout, f'Downloading {source_filename}')
		directory = settings.MEDIA_ROOT / 'sources' / 'retained'
		source_path = directory / source_filename
		previous_path = directory.parent / source_filename

		if not source_path.exists() and previous_path.is_file():
			directory.mkdir(parents=True, exist_ok=True)
			source_path.hardlink_to(previous_path)

		source_path = download_file(source_url, directory, progress.update)
		self.source_paths.add(source_path)

		self.stdout.write(f'Ready: {source_filename}')

		return source_path
