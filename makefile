CURDIR=$(shell pwd)
DC_MASTER="dc_master.yaml"
DC_TEMP="docker-compose.yaml"
GLOBAL_PREFIX=docker-
DOCKER_IN_GROUPS=$(shell groups 2>/dev/null | grep "docker")
MYID=$(shell id -u)

# Set the user according to fork
ifeq ($(strip $(GLOBAL_PREFIX)),"scraper) 
	 USER=$USER
endif

ifeq ($(strip $(DOCKER_IN_GROUPS)),)
	 DC_CMD=sudo docker-compose
else
	 DC_CMD=docker-compose
endif


all: root_check preparations run_build run_bash
#scrape: root_check preparations run_build run_scrape
preps: root_check preparations
build: root_check preparations run_build
restart: run_restart
fromscratch: root_check preparations run_remove run_build
remove: root_check run_remove


root_check:
	 @if [ "${MYID}" = "0" ]; then \
		  echo Please do not run as root. It is neither recommended nor would it work.; \
	 fi
	 @exit

preparations:
	 mkdir -p ${CURDIR}/vol/data/
	 cat ${DC_MASTER} \
		  | sed 's|<USER>|${USER}|g' \
		  | sed 's|<CURDIR>|${CURDIR}|g' \
		  | sed 's|<GLOBAL_PREFIX>|${GLOBAL_PREFIX}|g' \
		  > ${DC_TEMP}

	 cat docker/dockerfile_master \
	 | sed 's|<USER>|$(USER)|g' \
	 | sed 's|<UID>|$(MYID)|g' \
	 > docker/dockerfile

run_build:
	 $(DC_CMD) build scraper

run_remove:
	 $(DC_CMD) down --rmi all
	 $(DC_CMD) rm --force

run_restart:
	 $(DC_CMD) restart

run_bash:
	 $(DC_CMD) run --rm scraper bash

#run_scrape:
#	 $(DC_CMD) run --rm scraper xvfb-run ./scrape.py -vv
