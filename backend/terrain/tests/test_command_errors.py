from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from terrain.models.SunlightPreparation import SunlightPreparation
from terrain.models.TerrainDataset import TerrainDataset
from terrain.services.terrain_surface import TerrainAnalysisUnavailable
from terrain.tests.fixtures import create_selection, create_study, create_terrain_dataset


@pytest.mark.django_db
class TestPrepareSunlightCommand:
	def setup_method(self):
		self.dataset = create_terrain_dataset()
		self.selection = create_selection()

	def test_unsupported_storage_is_an_operator_error(self):
		self.dataset.storage_format = TerrainDataset.StorageFormat.FLOAT32
		self.dataset.save(update_fields=['storage_format'])

		with pytest.raises(CommandError, match='completed database terrain import'):
			call_command('prepare_sunlight', self.dataset.pk, self.selection.pk, workers=1, stdout=StringIO())

		assert not SunlightPreparation.objects.exists()


@pytest.mark.django_db
class TestPreparePlanResultsCommand:
	def setup_method(self):
		self.study = create_study(create_terrain_dataset(), create_selection())

	def test_incompatible_results_are_reported_and_the_revision_rolls_back(self, monkeypatch):
		def incompatible(study):
			raise TerrainAnalysisUnavailable('Saved results use different terrain preparations or ephemerides.')

		monkeypatch.setattr('terrain.management.commands.prepare_plan_results.rebuild_combined_visibility', incompatible)

		with pytest.raises(CommandError, match='different terrain preparations'):
			call_command('prepare_plan_results', self.study.pk, stdout=StringIO())

		self.study.refresh_from_db()
		assert self.study.result_revision == self.study.reset_revision == 0
