from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

from core.management.progress import Progress
from core.services.downloads import download_file
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from terrain.services.lunar_feature_import import CATALOG_URL, import_lunar_features


class Command(BaseCommand):
	help = 'Download the USGS lunar name catalog and store its features in the database.'

	def handle(self, **options):
		try:
			progress = Progress(self.stdout, 'Downloading lunar names')
			source_path = download_file(CATALOG_URL, settings.MEDIA_ROOT / 'nomenclature', progress.update)
			progress = Progress(self.stdout, 'Storing lunar features')
			count = import_lunar_features(source_path, progress.update)
		except (OSError, ValueError, KeyError, BadZipFile, ParseError) as error:
			raise CommandError(f'Unable to import lunar features: {error}') from error

		self.stdout.write(self.style.SUCCESS(f'Stored {count} lunar features. The downloaded catalog was retained.'))
