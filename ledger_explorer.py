# -*- coding: utf-8 -*-
import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import logging
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import treelib
import urllib


# TODO
# - Show Era labels
# - make the LOOKUPs use constants, not numbers
#   - related: swap out the LOOKUP sliders for something more like a pushbutton selector
# - show more info in scatter label and hovertext
# - apply better colors, including fixing dark mode
# - Improve the status bar so it shows dates in more readable format, e.g., 2020·Q1
# - re-arrange areas so that controls are in the same plane as things they control
# - show loading icon when doing longer operations
# - have option for "Other" to collect smaller accounts, with depth control knob
# - make the ledger entries prettier (bigger fonts, less grid fluff, smaller date, shorter description w/full in hover)
# - put per month/per year into sunburst labels

#######################################################################
# Function definitions except for callbacks
#######################################################################


#######################################################################
# Initialize and set up formatting
#######################################################################

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG)


app = dash.Dash(__name__)

# this eliminates an error about 'A local version of http://localhost/dash_layout.css'
app.css.config.serve_locally = False

app.css.append_css(dict(external_url='http://localhost/dash_layout.css'))

pd.set_option('display.max_rows', None)  # useful for DEBUGging, put back to 10?



#######################################################################
# Declare the content of the page
#######################################################################
#######################################################################
# Callback functions
#######################################################################




if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0')
