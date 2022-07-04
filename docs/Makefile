all:    local

help:   ##          Print this
	@printf "\ncommands: \n\n"
	@fgrep -h "##" $(MAKEFILE_LIST) | sed -e 's/\(\:.*\#\#\)/\:\ /' | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'
	@printf "\n"

local: ## serve locally at http://0.0.0.0:8200/	
	python3 ledgex/index.py
