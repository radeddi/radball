#!/usr/bin/env python3


import time
import socket
import datetime 

try:
	# Python2
	import Tkinter as tk
except ImportError:
	# Python3
	import tkinter as tk


UDP_IP = ""
UDP_PORT = 1234

sock = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP
sock.settimeout(1)
sock.bind((UDP_IP, UDP_PORT))

def show():
	try:

		#print("hello")
		data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
		print(data)
		
		root.after(10, show)
	except socket.timeout:
		root.after(10, show)

root = tk.Tk()
		
root.after(100, show)
root.mainloop()
