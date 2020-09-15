from flask import Flask
import dash


server = Flask(__name__)
app = dash.Dash(__name__, server=server, suppress_callback_exceptions=True)


if __name__ == '__main__':
    app.run_server(host='0.0.0.0', Debug=False)
