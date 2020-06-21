SHELL := /bin/bash

all: publish_data dash  ##     publish data, dash

publish_data: ## publish output file and eras file to web
	cp transactions.csv /var/www/html/gnureport/transactions.csv
	cp eras.csv /var/www/html/


dash:   ##     publish css and start dash development server on :8050
	cp dash_layout.css /var/www/html/gnureport/
	python ledger_dashboard.py

help:   ##     Print this
	@printf "\ncommands: \n\n"
	@fgrep -h "##" $(MAKEFILE_LIST) | sed -e 's/\(\:.*\#\#\)/\:\ /' | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'
	@printf "\n"
