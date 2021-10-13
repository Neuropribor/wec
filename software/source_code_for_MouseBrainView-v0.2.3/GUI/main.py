#-------------------------------------------------------------------------------
# author:	Nikita Makarevich
# email:	nikita.makarevich@spbpu.com
# 2021
#-------------------------------------------------------------------------------
# Mouse Brain View
#-------------------------------------------------------------------------------
# Program to read and display data from brain-computer interface.
# Data is transmitted through Internet with TCP protocol.
#-------------------------------------------------------------------------------

# libs
import sys
import os
import numpy as np
from pathlib import Path
import ctypes # Set app id in Windows
import json
import socket
import errno
import time
# GUI
from PyQt5.QtCore import (

	Qt,
	QObject,
	QTimer,
	QThread,
	pyqtSignal,
	pyqtProperty,
	pyqtSlot,
	QSettings,
)
from PyQt5.QtWidgets import (
	QApplication,
	QMainWindow,
	QGridLayout,
	QFileDialog,
)
from PyQt5.QtGui import (
	QIcon,
	QPixmap,
	QTextCursor,
)
import pyqtgraph as pg
from queue import Queue
# local imports
from build.MainForm import Ui_MainWindow
import build.res

from client import MyClient
from CSVWorker import CSVWorker


# Shift values in np.array
def npshift(arr, num, cval=np.nan):
	result = np.empty_like(arr)
	if num > 0:
		result[:num] = cval
		result[num:] = arr[:-num]
	elif num < 0:
		result[num:] = cval
		result[:num] = arr[-num:]
	else:
		result = arr
	return result

class Main_window(QMainWindow):
	def __init__(self, parent, registry):
		#---------------------------------------------------------------------------#
		super(Main_window, self).__init__(parent)
		self._registry = registry
		self.ui = Ui_MainWindow()
		self.setWindowFlags(self.windowFlags() | Qt.WindowSystemMenuHint | Qt.WindowMinMaxButtonsHint)
		self.setWindowIcon(QIcon(':/icons/window_image.ico'))
		#---------------------------------------------------------------------------#
		if os.name == 'nt':
			myappid = 'PSPOD.MouseBrain.MouseBrainView.0'
			ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
		#---------------------------------------------------------------------------#
		self.ui.setupUi(self)
		pos = self.reg_read("Geometry", "MainWindow")
		if pos:
			self.restoreGeometry(pos)
		#---------------------------------------------------------------------------#
		self.ui.pb_connect.clicked.connect(self.on_pb_connect_click)
		self.ui.pb_data_flow.clicked.connect(self.on_pb_data_flow_click)
		self.ui.pb_csv_dir.clicked.connect(self.on_pb_csv_dir_click)
		#---------------------------------------------------------------------------#
		self.pixmap_ok	  = QPixmap(':/icons/ok.png')
		self.pixmap_error = QPixmap(':/icons/error.png')
		self.pixmap_wait  = QPixmap(":/icons/sandclock.png")
		#---------------------------------------------------------------------------#
		self.autoconf_template = {
			'line_ip'       : '192.168.2.213',
			'line_port_com' : '1020',
			'line_port_dat' : '1000',
			'line_csv_dir'  : (Path(__file__).parent / "csv")
		}
		# Load settings from local json file
		if os.path.exists(Path(__file__).parent / 'autoconf.json'):
			with open(Path(__file__).parent / 'autoconf.json', 'r') as json_file:
				try:
					self.autoconf = json.load(json_file)
				except:
					print("Could not read settings file \"autoconf.json\"")
					self.autoconf = {}
		else: self.autoconf = {}
		
		self.ui.line_ip.setText      (self.autoconf.get('line_ip' , self.autoconf_template['line_ip']))
		self.ui.line_port_com.setText(self.autoconf.get('line_port_com' , self.autoconf_template['line_port_com']))
		self.ui.line_port_dat.setText(self.autoconf.get('line_port_dat' , self.autoconf_template['line_port_dat']))
		self.ui.line_csv_dir.setText (self.autoconf.get('line_csv_dir', str(self.autoconf_template['line_csv_dir'].resolve())))
		#---------------------------------------------------------------------------#
		self.client = MyClient(self)
		self.client.state_changed.connect(self.on_net_state_changed)
		self.client.command_signal.connect(self.on_net_command)
		self.client.data_signal.connect(self.on_net_data)
		self.client.connection_error_signal.connect(self.on_net_error)
		#---------------------------------------------------------------------------#
		self.olddat = b''
		pg.setConfigOption('background', 'w')
		pg.setConfigOption('foreground', 'k')
		self.plots_init(32)
		self.ui.splitter.setStretchFactor(1, 1)
		self.ui.splitter.setSizes([500,100])
		#---------------------------------------------------------------------------#
		self.write_csv_flag = False
		self.csvqq = Queue()
		self.csvww = CSVWorker(self.csvqq, Path(self.ui.line_csv_dir.text()))
		#---------------------------------------------------------------------------#
		#---------------------------------------------------------------------------#
		#--------------------------------[__INIT__ END]-----------------------------#
		#---------------------------------------------------------------------------#
	
	# Closing main window
	def closeEvent(self, event):
		if self.client.state >= MyClient.STATE_COM_CONNECTED:
			self.flow_stop()
			self.client.disconnect_from_host()
		
		# Save window geometry into registry to restore it later
		self.reg_save("Geometry", "MainWindow", self.saveGeometry())
		
		# Save settings into local json file
		self.autoconf['line_ip']        = self.ui.line_ip.text()
		self.autoconf['line_port_com']  = self.ui.line_port_com.text()
		self.autoconf['line_port_dat']  = self.ui.line_port_dat.text()
		self.autoconf['line_csv_dir']   = self.ui.line_csv_dir.text()
		with open(Path(__file__).parent / 'autoconf.json', 'w') as json_file:
			try:
				json.dump(self.autoconf, json_file)
			except:
				print("Could not save settings file")
		event.accept()
	
	@pyqtSlot(int)
	def on_net_state_changed(self, state):
		if state == MyClient.STATE_DISCONNECTED:
			self.ui.pb_connect.setText('Connect')
			self.clear_pixmap(self.ui.label_icon_connect)
			self.ui.pb_data_flow.setText('Start')
			self.message('Disconnected<br>')
			
		elif state == MyClient.STATE_COM_CONNECTING:
			self.message('Connecting to command port<br>')
			self.set_pixmap(self.ui.label_icon_connect, self.pixmap_wait)
		
		elif state == MyClient.STATE_DAT_CONNECTING:
			self.message('Connecting to data port<br>')
			self.set_pixmap(self.ui.label_icon_connect, self.pixmap_wait)
			
		elif state == MyClient.STATE_COM_CONNECTED:
			self.ui.pb_connect.setText('Disconnect')
			self.set_pixmap(self.ui.label_icon_connect, self.pixmap_ok)
		
		elif state == MyClient.STATE_DAT_CONNECTED:
			self.ui.pb_connect.setText('Disconnect')
			self.set_pixmap(self.ui.label_icon_connect, self.pixmap_ok)
	
	@pyqtSlot(str)
	def on_net_command(self, msg):
		self.message("%s<br>" % msg)
	
	busy = False
	@pyqtSlot(bytes)
	def on_net_data(self, dat):
		if self.busy:
			self.message('ERROR - trying to re-enter busy function<br>')
			return
		else: self.busy = True
		
		#print(np.frombuffer(dat, dtype=np.uint16))
		n_plots = len(self.curves)
		self.olddat = self.olddat + dat
		if len(self.olddat) >= n_plots * 2:
			# Split full plots representation and not completed part
			n_left = len(self.olddat) % (n_plots * 2)
			n_rows = int(np.floor(len(self.olddat) / (n_plots * 2)))
			if n_left == 0:
				buffer = np.frombuffer(self.olddat, dtype=np.uint16)
				self.olddat = b''
			else:
				buffer = np.frombuffer(self.olddat[:-n_left], dtype=np.uint16)
				self.olddat = self.olddat[-n_left:]
			# Process for plot
			for i in range(n_rows):
				for j in range(n_plots):
					self.curvebuffers[j] = npshift(self.curvebuffers[j], -1, buffer[i*n_plots + j])
					# ===================== Warning! time-critical function! ===
					if i == n_rows-1: self.curves[j].setData(self.curvebuffers[j])
					# ==========================================================
				if self.client.state >= MyClient.STATE_FLOW and self.write_csv_flag:
					self.csvqq.put(buffer[i*n_plots:(i+1)*n_plots])
					
		#print("olddat len: %d" % len(self.olddat))
		self.busy = False
	
	@pyqtSlot(socket.error)
	def on_net_error(self, e):
		if self.net_error_busy:
			return
		self.net_error_busy = True
		
		print(e)
		self.set_pixmap(self.ui.label_icon_connect, self.pixmap_error)
		if type(e) is socket.timeout:
			self.message('<font style=\"color:#CC00CC\";>Timeout</font><br>')
			#self.clear_pixmap(self.ui.label_icon_connect)
			self.net_error_busy = False
			return
		if type(e) is socket.error:
			print(os.strerror(e.errno))
			if e.errno == errno.ECONNRESET:
				self.flow_stop()
				self.message('<font style=\"color:#CC0000\";>Broken connection</font><br>')
				try:
					self.client.disconnect_from_host()
				except:
					pass
			else:
				self.flow_stop()
				try:
					self.client.disconnect_from_host()
				except:
					pass
				self.message("<font style=\"color:#CC0000\";>Connection error. Code: {}</font><br>".format(os.strerror(e.errno)))
		
		self.ui.pb_data_flow.setText('Start')
		self.net_error_busy = False
	net_error_busy = False
	
	def reg_save(self, section, name, value):
		self._registry.beginGroup(section)
		self._registry.setValue(name, value)
		self._registry.endGroup()
	
	def reg_read(self, section, name, default=None):
		self._registry.beginGroup(section)
		val = self._registry.value(name) or default
		self._registry.endGroup()
		return val
	
	def message(self, s):
		text_cursor = self.ui.messages.textCursor()
		text_cursor.clearSelection()
		self.ui.messages.setTextCursor(text_cursor)
		self.ui.messages.insertHtml(s)
		#if self.ui.cb_log_scroll.isChecked():
		self.ui.messages.moveCursor(QTextCursor.End)
	
	def set_pixmap(self, target, pm):
		target.setPixmap(
				pm.scaled(
					target.width(), 
					target.height(), 
					Qt.KeepAspectRatio
				)
			)
	def clear_pixmap(self, target):
		target.clear()
	
	def perform_command(self, cmd):
		self.message("<b>%s</b><br>" % cmd)
		ans = self.client.command(cmd)
		return ans
	
	def flow_stop(self):
		self.client.flow_stop()
		self.perform_command('`exec-stream_off;')
		self.ui.pb_data_flow.setText('Start')
		self.csvww.running = False
	
	def on_pb_connect_click(self):
		if self.client.state >= MyClient.STATE_COM_CONNECTED:
			# then disconnect
			self.message('Disconnecting<br>')
			self.flow_stop()
			try: self.client.disconnect_from_host()
			except: pass
		else:
			# then connect
			self.message('Connecting to %s:%i<br>' % (self.ui.line_ip.text(), int(self.ui.line_port_com.text())))
			self.client.hostname = self.ui.line_ip.text()
			self.client.port_com = int(self.ui.line_port_com.text())
			self.client.connect_to_host_com()
			if self.client.state >= MyClient.STATE_COM_CONNECTED:
				self.perform_command('`ver;')
				self.perform_command('`get-samplerate;')
				self.perform_command('`get-ch_count;')
	
	def on_pb_data_flow_click(self):
		if self.client.state >= MyClient.STATE_COM_CONNECTED:
			if self.client.flow_is_active:
				self.flow_stop()
			else:
				dsp_code_text = self.ui.combo_dsp_cutoff.currentText()
				dsp_code = int(dsp_code_text.split(':', 1)[0])
				self.perform_command("`set-samplerate:%d;" % int(self.ui.combo_samplerate.currentText()))
				self.perform_command("`set-low_bw:%d;" % round(float(self.ui.combo_lowpass.currentText()) * 1000))
				self.perform_command("`set-high_bw:%d;" % int(self.ui.combo_highpass.currentText()))
				self.perform_command("`set-dsp_en:%d;" % int(1 if self.ui.cb_dsp_enable.isChecked() else 0))
				self.perform_command("`set-dsp_code:%d;" % dsp_code)
				self.perform_command('`exec-apply;')
				
				if self.client.state >= MyClient.STATE_COM_CONNECTED and self.client.state < MyClient.STATE_FLOW:
					self.write_csv_flag = self.ui.cb_write_csv.isChecked()
					if self.write_csv_flag:
						self.csvqq = Queue()
						self.csvww = CSVWorker(self.csvqq, Path(self.ui.line_csv_dir.text()))
						self.csvww.running = True
						self.csvtt = QThread()
						self.csvww.moveToThread(self.csvtt)
						self.csvtt.started.connect(self.csvww.run)
						self.csvww.finished.connect(self.csvtt.quit)
						self.csvww.finished.connect(self.csvww.deleteLater)
						self.csvtt.finished.connect(self.csvtt.deleteLater)
						self.csvtt.start()
					
						self.csvqq.put(['Sample rate', self.ui.combo_samplerate.currentText()])
						self.csvqq.put(['Low-pass',    self.ui.combo_lowpass.currentText()])
						self.csvqq.put(['High-pass',   self.ui.combo_highpass.currentText()])
						self.csvqq.put(['DSP enable',  self.ui.cb_dsp_enable.isChecked()])
						self.csvqq.put(['DSP cutoff freq', dsp_code_text])
						self.csvqq.put(["ch%d" % (i+1) for i in range(32)])

					self.perform_command('`get-status;')
					self.perform_command('`exec-stream_on;')
					time.sleep(0.5)
					self.client.connect_to_host_dat()
					if self.client.state >= MyClient.STATE_DAT_CONNECTED:
						self.client.flow_start()
						self.ui.pb_data_flow.setText('Stop')
					else:
						self.client.disconnect_from_host()
		else:
			self.message('Error - device is not connected<br>')
	
	def on_pb_clear_log_click(self):
		self.ui.messages.clear()
	
	def on_pb_save_log_click(self):
		options = QtWidgets.QFileDialog.Options()
		filename, _ = QtWidgets.QFileDialog.getSaveFileName(
			self,
			"Save log as", 
			'',
			"HTML(*.html);;Text File(*.txt);;All Files(*)", 
			'',
			options
		)
		if filename:
			with open(filename, "w") as log_file:
				if (filename.endswith('html')):
					print(self.ui.messages.toHtml().encode(sys.stdout.encoding, errors='replace'), file=log_file)
				else:
					print(self.ui.messages.toPlainText().encode(sys.stdout.encoding, errors='replace'), file=log_file)
				self.message("Log saved successfully<br>")
	
	def on_pb_csv_dir_click(self):
		dirname = QFileDialog.getExistingDirectory(self, "Select Directory")
		if dirname:
			self.ui.line_csv_dir.setText(dirname)
	
	def plots_init(self, n_plots):
		# clear old grid layout
		while self.ui.plot_layout.count():
			item = self.ui.plot_layout.takeAt(0)
			widget = item.widget()
			if widget is not None:
				widget.setParent(None)
		
		self.grid = QGridLayout()
		self.ui.plot_layout.addLayout(self.grid)
		
		if (n_plots == 32): width = 8
		if (n_plots == 16): width = 4
		n_samples = 100
		self.curves = []
		self.curvebuffers = np.zeros((n_plots, n_samples), dtype=np.uint16)
		
		for i in range(n_plots):
			p = pg.PlotWidget()
			p.showGrid(x = True, y = True, alpha = 1)
			self.curves.append(p.plot(pen='b'))
			self.grid.addWidget(p, int(i / width), int(i % width))


class Main_app(QApplication):
	def __init__(self):
		QApplication.__init__(self, sys.argv)
		self.registry = QSettings('MouseBrainView', 'main_gui')
		try:
			pass
		except OSError as e:
			QMessageBox.critical(None, 'Error', str(e))
	
	def init(self):
		self.mainwin = Main_window(None, self.registry)
		self.mainwin.show()


if __name__ == "__main__":
	app = Main_app()
	app.init()
	sys.exit(app.exec_())
