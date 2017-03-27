import threading

def start_daemon_thread(target, args=[]):
	temp_thread = threading.Thread(target=target, args=args)
	temp_thread.daemon = True
	temp_thread.start()