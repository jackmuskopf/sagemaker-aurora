PYTHON_CMD=/usr/local/bin/python3

setup:
	${PYTHON_CMD} py-mgr/mgr.py setup

init:
	terraform init

apply:
	terraform apply

start:
	${PYTHON_CMD} py-mgr/mgr.py start --watch

stop:
	${PYTHON_CMD} py-mgr/mgr.py stop --watch

output:
	terraform output