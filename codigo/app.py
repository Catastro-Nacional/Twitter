import dash
import dash_core_components as dcc
import dash_html_components as html
import warnings
warnings.filterwarnings('ignore')
from flask_caching import Cache
import time

import plotly.graph_objs as go
from dash.dependencies import Input, Output
import numpy as np
from multiprocessing import Process, Queue

from utils import get_latest_output, read_mongo, json_pandas
from main import get_keywords
from utils_app import get_tpm, get_tpm_users, create_wc, get_username_list, get_users_indices


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# global variables
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
dir_noticias = 'data/Noticieros Twitter.csv'
dir_politicos = 'data/Politicos-Twitter.csv'

keywords = get_keywords()[:9]
noticieros = get_username_list(dir_noticias)
politicos = get_username_list(dir_politicos)

json_data = None
data_chile, data_prensa, data_politicos = {}, {}, {}
wc_chile, wc_prensa, wc_politicos = go.Figure({}), go.Figure({}), go.Figure({})


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# layout
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

fig_tpm_prensa = dcc.Graph(id='plot-tweets-prensa')
fig_tpm_chile = dcc.Graph(id='plot-tweets-chile')
fig_tpm_politicos = dcc.Graph(id='plot-tweets-politico')

fig_wc_prensa = dcc.Graph(id='word-cloud-prensa')
fig_wc_chile = dcc.Graph(id='word-cloud-chile')
fig_wc_politicos = dcc.Graph(id='word-cloud-politico')

# Dash object
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
CACHE_CONFIG = {
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache-directory'
}
cache = Cache()
cache.init_app(app.server, config=CACHE_CONFIG)


# layout for Dash object
app.layout = html.Div([

    # ======== PRESENTACION PAGINA ======== #

    html.H1(children='¡Bienvenid@ al DashBoard del CeMAS!', style={'textAlign': 'center'}),
    html.H5(children='''
    En esta página usted tiene acceso a distintas visualizaciones referentes a la situación
    actual de Chile.
    ''', style={'textAlign': 'center'}),

    html.H6(children="El objetivo es  que la ciudadanía tenga un fácil acceso a lo que estan diciendo los actores "
                     "políticos, los medios de comunicación y la ciudadanía",
            style={'textAlign': 'center'}),

    # ======== TABS PRENSA, CHILE, POLITICOS ======== #

    dcc.Tabs(id='tabs-graphs', value='tab-chile', children=[
        dcc.Tab(label='Prensa', id='graphs-prensa', value='tab-prensa', children=html.Div([
            html.H6(
                children="Los distintos medios de comunicación chilenos utilizan .  En tiempo real, se puede ver la cantidad de Tweets realizadas por la prensa:",
                style={'textAlign': 'center'}),
            html.Div(fig_tpm_prensa, style={'textAlign': 'center'}),

            html.H6("En donde las palabras que más usadas en sus tweets son:",
                    style={'textAlign': 'center'}),
            html.Div(fig_wc_prensa, style={'textAlign': 'center', 'display': 'flex', 'justify-content': 'center'})
        ])
                ),

        dcc.Tab(label='Chile', id='graphs-chile', value='tab-chile', children=html.Div([
            html.H6(
                children="Los chilenos también usan Twitter.  En tiempo real, se puede ver la frecuencia en que la gente utiliza la red social para expresarse:",
                style={'textAlign': 'center'}),
            html.Div(fig_tpm_chile, style={'textAlign': 'center'}),

            html.H6("Las palabras que más usan los usuarios de twitter son:",
                    style={'textAlign': 'center'}),
            html.Div(fig_wc_chile, style={'textAlign': 'center', 'display': 'flex', 'justify-content': 'center'}),
        ])
                ),

        dcc.Tab(label='Politicos', id='graphs-politicos', value='tab-politicos', children=html.Div([
            html.H6(
                children="Twitter se ha vuelto una plataforma importante para los políticos de hoy.  La frecuencia con la que publican en Twitter es:",
                style={'textAlign': 'center'}),
            html.Div(fig_tpm_politicos, style={'textAlign': 'center'}),

            html.H6("Las palabras que más usan los políticos para expresarse en Twitter son:",
                    style={'textAlign': 'center'}),
            html.Div(fig_wc_politicos, style={'textAlign': 'center', 'display': 'flex', 'justify-content': 'center'}),
            ])
        ),
    ]),

    # ======== hidden signal value ======== #
    html.Div(id='signal', style={'display': 'none'}),

    # ========  time interval ======== #
    dcc.Interval(id='interval',
                 interval=30 * 1000,  # in milliseconds
                 n_intervals=0),
])


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# functions
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
@cache.memoize()
def global_store(num_limit=None):
    # Read data from db and return json
    return read_mongo('dbTweets', 'tweets_chile',
                      query_fields={"dateTweet": 1, "tweet": 1, "screenName": 1},
                      json_only=True, num_limit=num_limit)


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# callbacks
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
@app.callback(
    Output('signal', 'children'),
    [Input('interval', 'n_intervals')]
)
def compute_data(_):
    global json_data
    json_data = json_pandas(global_store(num_limit=None))
    return None


# tweets per minute callbacks
@app.callback(
    Output('plot-tweets-prensa', 'figure'),
    [Input('signal', 'children'), Input('tabs-graphs', 'value')]
)
def update_graphs_prensa(_, tab):
    global data_prensa
    if(tab == 'tab-prensa' and json_data is not None):
        noticias_indices = get_users_indices(json_data, noticieros)
        tpm = get_tpm_users(json_data, noticias_indices, keywords)

        traces = [go.Scatter(x=tpm.index, y=tpm[col].values, mode='lines+markers',
                  text=col, name=col) for col in keywords + ['All']]

        data_prensa = {'data':traces}
        return go.Figure(data_prensa)
    else:
        return go.Figure(data_prensa)


@app.callback(
    Output('plot-tweets-politico', 'figure'),
    [Input('signal', 'children'), Input('tabs-graphs', 'value')]
)
def update_graphs_politicos(_, tab):
    global data_politicos
    if(tab == 'tab-politicos' and json_data is not None):
        idx = get_users_indices(json_data, politicos)
        tpm = get_tpm_users(json_data, idx, keywords)

        traces = [go.Scatter(x=tpm.index, y=tpm[col].values, mode='lines+markers',
                  text=col, name=col) for col in keywords + ['All']]

        data_politicos = {'data':traces}
        return go.Figure(data_politicos)
    else:
        return go.Figure(data_politicos)


@app.callback(
    Output('plot-tweets-chile', 'figure'),
    [Input('signal', 'children'), Input('tabs-graphs', 'value')]
)
def update_graphs_chile(_, tab):
    global data_chile
    if(tab == 'tab-chile' and json_data is not None):
        tpm = get_tpm(json_data, keywords)

        traces = [go.Scatter(x=tpm[key].index, y=tpm[key]['dateTweet'].values,
                  mode='lines+markers', text=key, name=key)
                  for key in keywords + ['All']]

        data_chile = {'data': traces}
        return go.Figure(data_chile)
    else:
        return go.Figure(data_chile)


# WordCloud callbacks
@app.callback(
    Output('word-cloud-prensa', 'figure'),
    [Input('signal', 'children'), Input('tabs-graphs', 'value')]
)
def update_wc_prensa(_, tab):
    global wc_prensa
    if(tab == 'tab-prensa' and json_data is not None):
        wc_prensa = create_wc(json_data, keywords)
        return wc_prensa
    else:
        return wc_prensa


@app.callback(
    Output('word-cloud-politico', 'figure'),
    [Input('signal', 'children'), Input('tabs-graphs', 'value')]
)
def update_wc_politicos(_, tab):
    global wc_politicos
    if(tab == 'tab-politico' and json_data is not None):
        wc_politicos = create_wc(json_data, keywords)
        return wc_politicos
    else:
        return wc_politicos

@app.callback(
    Output('word-cloud-chile', 'figure'),
    [Input('signal', 'children'), Input('tabs-graphs', 'value')]
)
def update_wc_chile(_, tab):
    global wc_chile
    if(tab == 'tab-chile' and json_data is not None):
        wc_chile = create_wc(json_data, keywords)
        return wc_chile
    else:
        return wc_chile


if __name__ == '__main__':
    app.run_server(debug=True)
