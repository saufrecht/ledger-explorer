import dash

app = dash.Dash(__name__, suppress_callback_exceptions=True)

# this eliminates an error about 'A local version of http://localhost/dash_layout.css'
app.css.config.serve_locally = False

app.css.append_css(dict(external_url='http://localhost/dash_layout.css'))

server = app.server
