PYTHON_CMD=python

setup:
	${PYTHON_CMD} py-mgr/mgr.py setup

init:
	terraform init

apply:
	terraform apply

start:
	${PYTHON_CMD} py-mgr/mgr.py start

stop:
	${PYTHON_CMD} py-mgr/mgr.py stop

output:
	terraform output