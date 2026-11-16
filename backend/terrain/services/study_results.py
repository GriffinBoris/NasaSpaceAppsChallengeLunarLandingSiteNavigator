def result_changes(study, after_revision):
	reset_history = after_revision is None or after_revision < study.reset_revision or after_revision > study.result_revision
	frames = study.frames.all()

	if not reset_history:
		frames = frames.filter(result_revision__gt=after_revision)

	return frames, reset_history
