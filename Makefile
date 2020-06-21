SHELL := /bin/bash

all: publish_data dash  ##     publish data, dash

publish_data: ## publish output file and eras file to web
	cp sample_data.csv /var/www/html/transactions.csv

dash:   ##     publish css and start dash development server on :8050
	python ledger_dashboard.py

help:   ##     Print this
	@printf "\ncommands: \n\n"
	@fgrep -h "##" $(MAKEFILE_LIST) | sed -e 's/\(\:.*\#\#\)/\:\ /' | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'
	@printf "\n"
