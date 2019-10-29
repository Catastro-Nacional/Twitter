import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import numpy as np
import io
from wordcloud import WordCloud
from PIL import Image
import plotly.graph_objs as go
from dash.dependencies import Input, Output

from utils import get_latest_output, read_mongo
from main import get_keywords

# direction of the csv file
latest_csv = get_latest_output()

# df = pd.read_csv(latest_csv)


key_words = get_keywords()


# ============== FUNCIONES =============== #

def get_kw_dict(dataframe):
    '''
        devuelve un diccionario con los índices del df que contienen cada una de las palabras clave
        ojo, eso no tiene pq sumar el total, ya que puden haber tweets con ambas palabras
    '''
    return {key_words[i]: dataframe[dataframe['text'].str.contains(key_words[i])].index for i in range(len(key_words))}


def key_word_filter(df, kw, kwdict):
    """
    filtra el dataframe entregado con la palabra clave pedida usando el diccionario
    :param df: pandas dataframe to filter
    :param kw: keyword to look for
    :param kwdict: dictionary with the index values for the words
    :return: a pd dataframe with the filteres request
    """
    return df.iloc[kwdict[kw]]


def tweets_per_minute():
    '''
    Generates a dataframe with the tweets per minute from a given df

    :return dataframe: Number of tweets per minute
    '''
    df = read_mongo('dbTweets', 'tweets_chile')

    # Particion de minuto de creacion de tweet
    df_minutos = pd.to_datetime(df['created_at']).dt.floor('min')

    # Obtiene el último minuto (ie el maximo). Es un 'supremo'
    max_date = df_minutos.max()

    # Hasta el ultimo minuto
    df_minutos = pd.to_datetime(df_minutos.loc[df_minutos < max_date]).dt.floor('min')

    # Se obtiene frecuencias por minuto
    frecuencias = df_minutos.sort_index().value_counts()

    # Diccionario
    data = {'date': frecuencias.index, 'freq': frecuencias.values}

    # Se ordena en un dataframe
    data = pd.DataFrame(data).sort_values('date')

    # Están contados los tweets por minuto para que se grafiquen
    return data


def get_word_frequency(dataframe, wordlist):
    """
    Count how many tweets contain a given word
    :param dataframe: Pandas dataframe from the tweepy mining
    :param wordlist: array-like with the keywords
    
    TODO: - drop dependency on numpy?
    """
    word_freq = dict()
    for word in wordlist:
        word_freq[word] = np.where(dataframe['text'].str.contains(word))[0].size

    return word_freq


def create_wordcloud_raster(dataframe, wordlist,
                            wc_kwargs=dict(background_color='white', colormap='plasma', width=1200, height=800)):
    """
    Generate a wordcloud of the keywords given, wheighted by the number of 
    unique tweets they appear in.
    :param dataframe: Pandas DataFrame object. It must contain a 'text' column with the
    tweets from the stream.
    :param wordlist: list of strings to plot in the word cloud.
    :param wc_kwargs: dict of keyword arguments to give to the WordCloud
    constructor.
    """
    wf = get_word_frequency(dataframe, wordlist)
    word_cloud = WordCloud(**wc_kwargs).generate_from_frequencies(wf)
    return Image.fromarray(word_cloud.to_array())


# ============== FIN FUNCIONES =============== #


# ACÁ SE VAN A CONSTRUIR LAS PARTES DE LA APP, EN ESPECÍFICO, DE LA PARTE DE PALABRAS #

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
    figure,
    time_interval
])


@app.callback(
    Output('plot', 'figure'),  # the output is what to modify and which property
    [Input('interval', 'n_intervals')]  # input is the trigger and the property
)
def update_graph(n):  # no sé pq está esa 'n' ahí, pero no la saquen que si no no funciona
    # update a pandas DataFrame

    data = tweets_per_minute()

    # assign the 'created_at' column to the histogram
    data = {
        'data': [go.Scatter(
            x=data['date'][1:],  # se salta el primer elemento porque no es el minuto completo
            y=data['freq'][1:],
            mode='lines+markers'
        )]
    }

    return go.Figure(data)  # returns the figure to be updated


if __name__ == '__main__':
    app.run_server(debug=True)
