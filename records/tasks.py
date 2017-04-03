from KanCompDetector_site.celery import app

class AddTask(app.Task):
	def __init__(self):
		self.number = 0
	def run(self, x):
		self.number += x
		return self.number

add = app.register_task(AddTask())