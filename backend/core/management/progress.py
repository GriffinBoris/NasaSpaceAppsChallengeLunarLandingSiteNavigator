class Progress:
	def __init__(self, output_stream, progress_label):
		self.output_stream = output_stream
		self.progress_label = progress_label
		self.last_percentage = -1

	def update(self, completed_units, total_units):
		if not total_units:
			self.output_stream.write(f'{self.progress_label}: {completed_units / 1024 / 1024:.1f} MB', ending='\r')
			self.output_stream.flush()

			return

		percentage = min(100, completed_units * 100 // total_units)

		if percentage == self.last_percentage:
			return

		self.last_percentage = percentage
		line_ending = '\n'

		if self.output_stream.isatty() and percentage < 100:
			line_ending = '\r'

		self.output_stream.write(f'{self.progress_label}: {percentage:3d}%', ending=line_ending)
		self.output_stream.flush()
