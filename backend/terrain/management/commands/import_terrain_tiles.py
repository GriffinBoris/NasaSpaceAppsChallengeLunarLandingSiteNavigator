from core.management.progress import Progress
from django.core.management.base import BaseCommand, CommandError

from terrain.models.TerrainDataset import TerrainDataset
from terrain.services.file_import import import_file_tiles


class Command(BaseCommand):
	help = 'Copy one completed file-based terrain dataset into database tile rows without resampling the raw sources.'

	def add_arguments(self, parser):
		parser.add_argument('dataset_id', type=int)

	def handle(self, **options):
		try:
			source_dataset = TerrainDataset.objects.get(pk=options['dataset_id'])
		except TerrainDataset.DoesNotExist as error:
			raise CommandError('Terrain dataset does not exist.') from error

		progress = Progress(self.stdout, 'Storing tile rows')

		try:
			dataset = import_file_tiles(source_dataset, progress.update)
		except (OSError, ValueError) as error:
			raise CommandError(str(error)) from error

		self.stdout.write(self.style.SUCCESS(f'Stored {dataset.tile_count} tile rows as dataset {dataset.pk}. Original files were retained.'))
