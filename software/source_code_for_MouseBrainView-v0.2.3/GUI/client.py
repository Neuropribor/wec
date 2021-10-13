#-------------------------------------------------------------------------------
# author:	Nikita Makarevich
# email:	nikita.makarevich@spbpu.com
# 2021
#-------------------------------------------------------------------------------
# Mouse Brain View
#-------------------------------------------------------------------------------
# TCP-client
# Connects to the server on main sensor board
#-------------------------------------------------------------------------------

import socket

from PyQt5.QtCore import (
	QObject, QTimer,
	pyqtSignal, pyqtProperty, pyqtSlot
)

# TCP client
class MyClient(QObject):
	STATE_DISCONNECTED   = 0
	STATE_COM_CONNECTING = 1
	STATE_COM_CONNECTED  = 2
	STATE_DAT_CONNECTING = 3
	STATE_DAT_CONNECTED  = 4
	STATE_FLOW      = 5

	connected = pyqtSignal(int)
	disconnected = pyqtSignal(int)

	state_changed = pyqtSignal(int)
	hostname_changed = pyqtSignal(str)
	port_com_changed = pyqtSignal(int)
	port_dat_changed = pyqtSignal(int)
	flow_changed = pyqtSignal(bool)
	
	command_signal = pyqtSignal(str)
	data_signal    = pyqtSignal(bytes)
	connection_error_signal = pyqtSignal(socket.error)

	def __init__(self, parent=None):
		super(MyClient, self).__init__(parent)

		self.m_hostname = ""
		self.m_port_com = 1020
		self.m_port_dat = 1000
		self.m_state = MyClient.STATE_DISCONNECTED

		# they will be re-created on connection
		self.socket_com = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.socket_dat = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		
		self.timer=QTimer()
		self.timer.timeout.connect(self.rx_data)
		self.timer.setSingleShot(True)
		self.timer.setInterval(1) # 1ms
	
	@pyqtSlot()
	def connect_to_host_com(self):
		self.socket_com = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.socket_com.settimeout(1.0) # 1s
		self.com_writer_obj = self.socket_com.makefile(mode='wb')
		
		self.state = MyClient.STATE_COM_CONNECTING
		try:
			self.socket_com.connect((self.m_hostname, self.m_port_com))
			self.state = MyClient.STATE_COM_CONNECTED
		except (socket.error, socket.timeout) as e:
			print('connect to command port: timeout')
			self.state = MyClient.STATE_DISCONNECTED
			self.connection_error_signal.emit(e)
	
	@pyqtSlot()
	def connect_to_host_dat(self):
		self.socket_dat = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.socket_dat.settimeout(1.0)
		self.state = MyClient.STATE_DAT_CONNECTING
		try:
			self.socket_dat.connect((self.m_hostname, self.m_port_dat))
			self.state = MyClient.STATE_DAT_CONNECTED
		except (socket.error, socket.timeout) as e:
			print('connect to data port: timeout')
			self.state = MyClient.STATE_DISCONNECTED
			self.connection_error_signal.emit(e)
	
	@pyqtSlot()
	def disconnect_from_host(self):
		self.flow_stop()
		if self.state >= MyClient.STATE_DAT_CONNECTED:
			self.socket_dat.shutdown(socket.SHUT_RDWR)
			self.socket_dat.close()
		
		if self.state >= MyClient.STATE_COM_CONNECTED:
			self.socket_com.shutdown(socket.SHUT_RDWR)
			self.socket_com.close()
		
		self.state = MyClient.STATE_DISCONNECTED
		
	
	def command(self, line):
		if self.state >= MyClient.STATE_COM_CONNECTED:
			try:
				#self.socket_com.sendall(line.encode("ascii", "replace"))
				self.com_writer_obj.write(line.encode("ascii", "replace"))
				self.com_writer_obj.flush()
				
				reply = self.socket_com.recv(1024)
				self.command_signal.emit(reply.decode("ascii"))
			except socket.error as e:
				self.connection_error_signal.emit(e)

	def rx_data(self):
		if self.state >= MyClient.STATE_FLOW:
			try:
				reply = self.socket_dat.recv(65536)
				if len(reply) != 0: self.data_signal.emit(reply)
			except socket.error as e:
				self.connection_error_signal.emit(e)
			finally:
				self.timer.start()

	def flow_start(self):
		if self.state >= MyClient.STATE_DAT_CONNECTED:
			self.state = MyClient.STATE_FLOW
			self.timer.start()
	def flow_stop(self):
		if self.state >= MyClient.STATE_FLOW:
			self.state = MyClient.STATE_DAT_CONNECTED
		self.timer.stop()
	
	@pyqtProperty(int, notify=state_changed)
	def state(self):
		return self.m_state
	
	@state.setter
	def state(self, state):
		if self.m_state == state: return
		self.m_state = state
		self.state_changed.emit(state)
	
	@pyqtProperty(int, notify=flow_changed)
	def flow_is_active(self):
		return self.state == MyClient.STATE_FLOW
	
	@pyqtProperty(str, notify=hostname_changed)
	def hostname(self):
		return self.m_hostname
	
	@hostname.setter
	def hostname(self, hostname):
		if self.m_hostname == hostname: return
		self.m_hostname = hostname
		self.hostname_changed.emit(hostname)
	
	@pyqtProperty(int, notify=port_com_changed)
	def port_com(self):
		return self.m_port_com
	
	@port_com.setter
	def port_com(self, port):
		if self.m_port_com == port: return
		self.m_port_com = port
		self.port_changed.emit(port)
	
	@pyqtProperty(int, notify=port_dat_changed)
	def port_dat(self):
		return self.m_port_dat
	
	@port_com.setter
	def port_dat(self, port):
		if self.m_port_dat == port: return
		self.m_port_dat = port
		self.port_changed.emit(port)
