#-------------------------------------------------------------------------------
# author:	Nikita Makarevich
# email:	nikita.makarevich@spbpu.com
# 2021
#-------------------------------------------------------------------------------
# Mouse Brain View
#-------------------------------------------------------------------------------

from PyQt5.QtCore import (
	QObject, pyqtSignal
)
from datetime import datetime
from queue import Queue
import time

import csv

class CSVWorker(QObject):
	finished = pyqtSignal()

	def __init__(self, queue, dirname, parent=None):
		super(CSVWorker, self).__init__(parent)
		self.qq = queue
		self.running = True
		
		try:
			now = datetime.now()
			dirname.mkdir(exist_ok=True)
			fname = dirname / now.strftime("data_%Y-%m-%d_%H-%M-%S.csv")
			self.ofile = open(fname, 'w', newline='')
			self.ocsv = csv.writer(self.ofile, quoting=csv.QUOTE_MINIMAL)
		except (FileNotFoundError, FileExistsError) as e:
			self.running = False
		
	def run(self):
		while self.running:
			if not self.qq.empty():
				values = self.qq.get()
				self.ocsv.writerow(values)
			else:
				time.sleep(1)
		else:
			del self.ocsv
			self.ofile.close()
			self.finished.emit()
