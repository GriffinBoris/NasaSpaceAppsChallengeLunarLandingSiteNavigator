from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from django.db import connections
from django.db.models import QuerySet
from django.urls import reverse

from terrain.models.SunlightStudy import SunlightStudy
from terrain.services import study_jobs
from terrain.tests.fixtures import create_selection, create_study, create_terrain_dataset


@pytest.mark.django_db(transaction=True)
class TestStudyDeletion:
	def setup_method(self):
		self.dataset = create_terrain_dataset()
		self.study = create_study(self.dataset, create_selection())

	def test_queueing_after_http_lookup_prevents_deletion(self, client, monkeypatch):
		published = []
		monkeypatch.setattr(study_jobs, 'publish_study', lambda study_id, run_id: published.append(study_id))

		def queue_before_delete(study_id):
			assert study_jobs.queue_study(study_id)
			return study_jobs.delete_study(study_id)

		monkeypatch.setattr('terrain.views.studies.views.delete_study', queue_before_delete)
		response = client.delete(reverse('terrain:studies:sunlight-study-detail', kwargs={'study_id': self.study.pk}))
		self.study.refresh_from_db()

		assert response.status_code == 409
		assert self.study.status == SunlightStudy.Status.QUEUED
		assert published == [self.study.pk]

	def test_deletion_claim_blocks_concurrent_queueing_on_sqlite(self, monkeypatch):
		queue_attempted = Event()
		original_delete = QuerySet.delete
		published = []
		monkeypatch.setattr(study_jobs, 'publish_study', lambda study_id, run_id: published.append(study_id))

		def queue_in_another_connection():
			try:
				queue_attempted.set()
				return study_jobs.queue_study(self.study.pk)
			finally:
				connections.close_all()

		with ThreadPoolExecutor(max_workers=1) as executor:
			queued = []

			def delete_after_queue_attempt(queryset):
				if queryset.model is SunlightStudy:
					queued.append(executor.submit(queue_in_another_connection))
					assert queue_attempted.wait(timeout=5)

				return original_delete(queryset)

			monkeypatch.setattr(QuerySet, 'delete', delete_after_queue_attempt)
			assert study_jobs.delete_study(self.study.pk)
			assert queued[0].result(timeout=5) is False

		assert not SunlightStudy.objects.filter(pk=self.study.pk).exists()
		assert published == []

	@pytest.mark.parametrize('route_name', ['sunlight-study-detail', 'sunlight-study-site-combined-visibility'])
	def test_missing_parent_wins_over_invalid_cursor(self, client, route_name):
		identifiers = {'study_id': self.study.pk + 1}

		if route_name == 'sunlight-study-site-combined-visibility':
			identifiers['selection_id'] = self.study.selections[0]['id']

		response = client.get(reverse(f'terrain:studies:{route_name}', kwargs=identifiers), {'after_revision': 'invalid'})

		assert response.status_code == 404

	def test_missing_pinned_selection_wins_over_invalid_cursor(self, client):
		url = reverse(
			'terrain:studies:sunlight-study-site-combined-visibility',
			kwargs={'study_id': self.study.pk, 'selection_id': self.study.selections[0]['id'] + 1},
		)

		response = client.get(url, {'after_revision': 'invalid'})

		assert response.status_code == 404
