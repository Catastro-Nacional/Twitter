import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objs as go
from dash.dependencies import Input, Output

from utils import get_latest_output
from main import get_keywords

# direction of the csv file
latest_csv = get_latest_output()

df = pd.read_csv(latest_csv)
key_words = get_keywords()


# ACÁ SE VAN A CONSTRUIR LAS PARTES DE LA APP, EN ESPECÍFICO, DE LA PARTE DE PALABRAS #

def get_kw_dict(dataframe):
    '''
    devuelve un diccionario con los índices del df que tienen la palabra
    '''
    return {key_words[i]: dataframe[dataframe['text'].str.contains(key_words[i])].index for i in range(len(key_words))}


# dropdown menu
options_dropdown = [{'label': 'TODO', 'value': 'All'}] + \
                   [{'label': key_words[i].upper(), 'value': key_words[i]} for i in range(len(key_words[:9]))]

dropdown_menu = dcc.Dropdown(
    id='dropdown',
    options=options_dropdown,
    value='All',
    multi=True,
    placeholder="Seleccione las palabras clave"
)

#  time inteval
time_interval = dcc.Interval(
    id='interval',
    interval=30 * 1 * 1000,  # in milliseconds
    n_intervals=0
)

# figure
figure = dcc.Graph(id='plot')

# ACÁ TERMINA #


texto_explicativo = "En esta página usted tiene acceso a distintas herramientas para filtrar los datos que desde el " \
                    "CeMAS dejamos a su disposición. "

# css
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']


# se crea un objeto dash
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# layout config
app.layout = html.Div([
    html.H1('¡Bienvenid@ al DashBoard del CeMAS!'),
    html.Div(texto_explicativo),
    dropdown_menu,

    # figure object
    figure,
    # interval in milliseconds to update the figure
    time_interval
])


# Dropdown
@app.callback(
    Output('plot', 'figure'),  # the output is what to modify and which property
    [Input('interval', 'n_intervals')]  # input is the trigger and the property
)


# how to update the figure
def update_graph(n):  # no sé pq está esa 'n' ahí, pero no la saquen que si no no funciona
    # update a pandas DataFrame

    data = getDf2plot(latest_csv)

    # assign the 'created_at' column to the histogram
    data = {
        'data': [go.Scatter(
            x=data['date'][1:],  # se salta el primer elemento porque no es el minuto completo
            y=data['freq'][1:],
            mode='lines+markers'
        )]
    }

    return go.Figure(data)  # returns the figure to be updated


def getDf2plot(filename):
    df = pd.read_csv(filename)

    DF = pd.to_datetime(df['created_at']).dt.floor('min')

    max_date = DF.max()
    DF = pd.to_datetime(DF.loc[DF < max_date])
    DF = DF.sort_index().value_counts()

    data = {'date': DF.index, 'freq': DF.values}
    data = pd.DataFrame(data).sort_values('date')
    return data


if __name__ == '__main__':
    app.run_server(debug=True)
