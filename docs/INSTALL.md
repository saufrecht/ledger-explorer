# Local Development Server

## get the code

`git clone https://github.com/saufrecht/ledger-explorer.git`

`cd ledger-explorer`

## Confirm Python version 3.8 or higher

Use `python --version` to confirm your version of Python.  It must be version 3.8.0 or higher.

* This version is included in Ubuntu 20.04.
* [Windows Download](https://www.python.org/downloads/windows/)

## Make and activate a virtual environment

The path for your virtual environment should not be inside the source-controlled ledger-explorer directory; if it is, you'll need to modify `.gitignore` to ignore it.  The ideal place for this directory depends on your local configuration.  One reasonable and safe choice on Mac/Linux is `~/.venv_le`.  On Windows, best practice is unclear (or unknown to your humble but lazy documenter).  Using a virtual environment is technically optional but a very very good idea. See [Python documentation on Virtual Environments](https://docs.python.org/3/tutorial/venv.html) for more information.

You will need to activate the virtual environment every time you open a new shell to run Ledger Explorer.

### Mac and Linux

1. `python3 -m venv /path/to/myenv`
2. `source /path/to/myenv/bin/activate`

### Windows

1. `c:\>c:\Python38\python -m venv c:\path\to\myenv`
2. `.\path\to\myenv\Scripts\activate`

### Install prerequisite Python modules

`pip install -r docs/requirements.txt`

## Prepare data

### Export data from Gnucash

1. `File` → `Export` → `Export Transactions to CSV …`
2. `Next`
3. `Select All`, `Next`
4. Enter filename, for example, `transactions.csv`

## Run program
1. `python ledger_explorer/index.py`
1. Browse to http://localhost:8050.
1. In the *Load File* » *Transaction File* » "Drag and Drop or Select Files" box, either
  1. Drop transactions.csv into the box from another window,
  1. Or, click 'Select Files' and select transactions.csv
1. If everything works, you should see something similar to the screenshot.

### Warnings
1. This is the development mode for Dash; do not deploy this on the web or otherwise use in a production environment.
1. Anyone on your local network, for example anyone on the same wifi, may be able to access this site.


# Production Server (Linux) ROUGH DRAFT, UNVERIFIED
A production-ready setup, using Nginx and GUnicorn.

## How it works

1. systemd manages an automatic service named **ledge**, which is always running
2. **ledge** calls on gunicorn, which runs the **ledger_explorer** code
    1. **ledger_explorer** is now accessible on a local unix socket
3. nginx takes HTTPS web requests to the public url and passes them to the unix socket, and then returns the response

## Prepare a production server

1. Create a new, non-root user for ledger explorer, let's call it **ledge**.
   1. `sudo adduser ledge`
2. Install nginx
   1. `sudo apt install nginx`
3. Set up HTTPS 
   1. `sudo apt install certbot python3-certbot-nginx`
   1. `sudo certbot --nginx -d *your-domain.name* -d *www.your.domain.name*`

## get the code
* Same as for development server (above).  Do this and all future steps as the new user, **ledge**, unless otherwise noted.

## Confirm Python version 3.8 or higher
* Same as for development server (above)

## Make and activate a virtual environment
* Same as for development server (above).

### Install prerequisite Python modules

1. `pip install -r docs/requirements.txt`
2. `pip install -r docs/requirements-prod-only.txt`

## Set Up Ledger Explorer to be run from Gunicorn
1. Test by running `gunicorn -b 127.0.0.1:8081 index:server`
   1. Should be able to access the site locally-only.  (use a public IP address if necessary to verify this step works)
2. Create a new systemd service file to control ledge:
   1. `sudo emacs /etc/systemd/system/ledge.service`
3. `sudo systemctl enable ledge.service`
4. `sudo systemctl start ledge.service`
5. Verify that the service is running correctly with `systemctl status ledge` (TODO: what should results look like)

### Contents of ledge.service

```
[Unit]
Description=Gunicorn instance to serve Ledger Explorer
After=network.target

[Service]
User=s
Group=www-data

WorkingDirectory=/home/ledge/ledger-explorer/ledger_explorer
Environment="PATH=/home/ledge/.venv_le/bin/"
ExecStart=/home/ledge/.venv_le/bin/gunicorn --workers 3 --bind unix:ledge.sock -m 007 index:server

[Install]
WantedBy=multi-user.target
```


## Configure Nginx as a proxy server for Gunicorn
1. Edit the nginx site configuration file for ledge (this file should already exist from initial setup and certbot)
    1. `sudo emacs /etc/nginx/sites-available/ledge`
    1. Verify that the config file has no errors: `sudo service nginx configtest`
2. `sudo service nginx restart`
3. Check: `service nginx status`

```
server {

        server_name your.server.name www.your.server.name;

        location /s/ {
                 root /var/www/ledge/html/;
        }

        location / {
                 include proxy_params;
                 proxy_pass http://unix:/home/ledge/ledger-explorer/ledger_explorer/ledge.sock;
        }

        
    listen [::]:443 ssl ipv6only=on; # managed by Certbot
    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/your.server.name/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/your.server.name/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot


}
server {
    if ($host = www.your.server.name) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


    if ($host = your.server.name) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


        listen 80;
        listen [::]:80;

        server_name your.server.name www.your.server.name;
    return 404; # managed by Certbot
}
```