import sys
import os
import subprocess

class Node(object):
	def __init__(self, address, port = 22, directory = "~/run", gpio_pins = "", serialport = "/dev/ttyUSB0", friendlyname = "", verbose = False):
		self.address = address
		self.port = port
		self.directory = directory
		self.verbose = verbose
		self.friendlyname = friendlyname
		self.serialport = serialport
		self.serialexport = "MY_SERIALPORT=" + self.serialport
		self.gpio_pins = gpio_pins
		self.gpio_pins_export = "MY_GPIOPINS=" + self.gpio_pins

	def syncfiles(self):
		cmdline = "rsync --exclude=wrapper.py --exclude=powercontrol.py --exclude=__pycache__ --exclude=*.pyc -q -e 'ssh -p %i' -r -h --progress ./ %s:%s" % (self.port, self.address, self.directory)
		if self.verbose:
			print(cmdline)
		os.system(cmdline)

	def runcommand(self, command):
		cmdline = "ssh -t -p %i %s 'cd %s; %s %s %s'" % (self.port, self.address, self.directory, self.serialexport, self.gpio_pins_export, command)
		if self.verbose:
			print(cmdline)
		os.system(cmdline)

	def getfile(self, filename):
		cmdline = "rsync --exclude=wrapper.py --exclude=__pycache__ --exclude=*.pyc -q -e 'ssh -p %i' -r -h --progress %s:%s/%s ./" % (self.port, self.address, self.directory, filename)
		if self.verbose:
			print(cmdline)
		os.system(cmdline)

	def sendfile(self, filename):
		cmdline = "rsync --exclude=wrapper.py --exclude=__pycache__ --exclude=*.pyc -q -e 'ssh -p %i' -r -h --progress ./%s %s:%s" % (self.port, filename, self.address, self.directory)
		if self.verbose:
			print(cmdline)
		os.system(cmdline)

	def reset(self):
		self.runcommand("python powercontrol.py reset")

	def power(self):
		self.runcommand("python powercontrol.py power")

	def forceoff(self):
		self.runcommand("python powercontrol.py forceoff")

	def powerstatus(self):
		self.runcommand("python powercontrol.py powerstatus")

	def isbusy(self):
		cmdline = "ps aux | grep \"python .*/%s\"" % (self.directory.replace("run", "r[u]n"))
		try:
			out = subprocess.check_output(["ssh", "-p", str(self.port), self.address, cmdline])
			return True
		except:
			return False

	def __str__(self):
		return "%s:%i:%s:%s:%s (%s)" % (self.address, self.port, self.directory, self.serialport, self.gpio_pins, self.friendlyname)

# add nodes here
# nodenames are unique lowercase strings
nodes = {}
nodes["n1"] = Node("pi@example.com", 22, "~/run/ttyUSB0", "26,24,22", "/dev/ttyUSB0", "K8, AMD Sempron 3100+", True)


def printhelp():
	print("Usage: %s sync|run|getfile|sendfile|isbusy|runshellcommand|listnodes|help|reset|power|forceoff|powerstatus node filename" % sys.argv[0])

def printnodes():
	for k,v in nodes.items():
		print("%s: %s" % (k,v))

def main(args):
	if len(args) < 2 or args[1] == "help":
		printhelp()
		return False

	command = args[1]

	if command == "listnodes":
		printnodes()
		return True

	# end single argument commands
	if len(args) < 3:
		printhelp()
		return False

	# try to resolve node
	nodename = args[2].lower()
	try:
		node = nodes[nodename]
	except:
		print("Unknown node %s" % nodename)
		print("Known nodes:")
		printnodes()
		return False

	if command == "sync":		
		node.syncfiles()
		return True

	if command == "isbusy":
		if node.isbusy():
			print("Node %s is currently busy" % nodename)
		else:
			print("Node %s is currently free" % nodename)
		return True

	if command == "reset":
		node.reset()
		return True
	if command == "power":
		node.power()
		return True
	if command == "forceoff":
		node.forceoff()
		return True

	if command == "powerstatus":
		node.powerstatus()
		return True

	# end double argument commands
	if len(args) < 4:
		printhelp()
		return False

	if command == "getfile":
		node.getfile(args[3])
		return True

	if command == "sendfile":
		node.sendfile(args[3])
		return True

	# concat all following args into one large arg with spaces
	# this is hacky, but allows running commands with arguments without needing to quote them
	if len(args) > 4:
		for i in range(4, len(args)):
			args[3] = args[3] + " " + args[i]

	if command == "runshellcommand":
		node.runcommand(args[3])
		return True

	if command == "run":
		if node.isbusy():
			print("Node %s is currently busy, not running command" % nodename)
			return False
		node.syncfiles()
		node.runcommand("python -u %s/%s" % (node.directory, args[3]))
		return True

	print("Invalid syntax")
	printhelp()
	return False

if __name__ == "__main__":
	main(sys.argv)