SHELL := /bin/bash

all: publish_data dev dash  ##          publish_data, dev, dash

publish_data: ## publish data content files to static webserver
	cp sample_data.csv /var/www/html/transactions.csv

dev: ##          publish any supporting files to static webserver
	cp dash_layout.css /var/www/html/

dash:   ##         publish css and start dash development server on :8050
	python ledger_explorer.py

help:   ##         Print this
	@printf "\ncommands: \n\n"
	@fgrep -h "##" $(MAKEFILE_LIST) | sed -e 's/\(\:.*\#\#\)/\:\ /' | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'
	@printf "\n"
