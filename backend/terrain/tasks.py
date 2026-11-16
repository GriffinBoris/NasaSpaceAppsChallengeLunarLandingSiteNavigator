from celery.signals import worker_shutting_down
from celery.worker.state import active_requests
from core.celery import app


@app.task(ignore_result=True, acks_late=True)
def calculate_study(study_id, run_id):
	from terrain.services.study_jobs import process_study

	process_study(study_id, run_id)


@worker_shutting_down.connect
def stop_active_studies(**signal_arguments):
	from terrain.services.study_jobs import stop_study

	for request in list(active_requests):
		if request.name == calculate_study.name:
			study_id, run_id = request.args
			stop_study(study_id, run_id)
