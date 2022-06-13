import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import altair as alt
import plotly.graph_objects as go
import plotly_express as px
import geopy
from geopy.extra.rate_limiter import  RateLimiter
import geopandas
import folium
import requests
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from time import sleep
import networkx as nx
from pyvis import network as net
from IPython.core.display import display, HTML
import streamlit.components.v1 as components
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, plot_roc_curve, roc_auc_score
import re

with st.echo(code_location='below'):

    @st.cache
    def get_data():
        return (pd.read_csv("the_oscar_award.csv"),
                pd.read_csv("oscars_df.csv"),
                pd.read_csv("movie_metadata.csv"))

    @st.cache
    def get_film_data(title):
        if(not title):
            return None

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
        driver.get("https://www.imdb.com/")

        search_box = (driver
                      .find_element(By.CSS_SELECTOR, "div.react-autosuggest__container")
                      .find_element(By.TAG_NAME, "input"))
        search_box.send_keys(title)
        sleep(2)

        first_result = driver.find_element(By.CSS_SELECTOR, "a.sc-bqyKva.ehfErK.searchResult.searchResult--const")
        first_result.click()
        sleep(2)

        film_url = driver.current_url

        director = driver.find_element(By.CSS_SELECTOR, "div.ipc-metadata-list-item__content-container")
        director_name = director.find_element(By.TAG_NAME, "a")

        cast_page = (driver
                     .find_element(By.CSS_SELECTOR, "div.ipc-title__wrapper")
                     .find_element(By.TAG_NAME, "a"))
        cast_page.click()
        sleep(1)

        cast_table = driver.find_element(By.CSS_SELECTOR, "table.cast_list").find_element(By.TAG_NAME, "tbody")
        cast_list = cast_table.find_elements(By.TAG_NAME, "tr")

        actors_names = []
        for actor in cast_list[1:]:
            el_class = actor.get_attribute("class")
            if (el_class != "odd" and el_class != "even"):
                break
            actor_name = actor.find_elements(By.TAG_NAME, "td")[1].find_element(By.TAG_NAME, "a").text
            actors_names.append(actor_name)

        return [actors_names, film_url]

    @st.cache
    def get_locations(film_url):
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
        driver.get(film_url)
        sleep(1)

        details = driver.find_element(By.CSS_SELECTOR, '[data-testid="title-details-section"]')
        filming_locations = details.find_element(By.CSS_SELECTOR, '[data-testid="title-details-filminglocations"]')
        loc = filming_locations.find_element(By.CSS_SELECTOR,
                                             "a.ipc-metadata-list-item__label.ipc-metadata-list-item__label--link")
        loc.click()
        loc = driver.find_element(By.ID, "filming_locations")
        pr = loc.find_elements(By.TAG_NAME, "div")
        all_locations = []
        for el in pr:
            el_class = el.get_attribute("class")
            if (el_class != "soda sodavote odd" and el_class != "soda sodavote even"):
                continue
            all_locations.append(el.find_element(By.TAG_NAME, "dt").find_element(By.TAG_NAME, "a").text)

        locator = geopy.Nominatim(user_agent="myGeocoder")

        df = pd.DataFrame({"address": all_locations})
        geocode = RateLimiter(locator.geocode, min_delay_seconds=0.01)
        df['location'] = df['address'].apply(geocode)
        df = df.dropna()
        df['point'] = df['location'].apply(lambda cr: tuple(cr.point))
        df[['latitude', 'longitude', 'altitude']] = pd.DataFrame(df['point'].tolist(), index=df.index)

        coor = df.loc[:, ["address", "latitude", "longitude"]]
        coor.loc[:, "coordinates"] = list(zip(coor["latitude"], coor["longitude"]))

        return [list(coor["address"]), list(coor["coordinates"])]


    def draw_locations(coordinates, all_locations):

        map = folium.Map(location=[40.76791227224293, -73.98658282967192], zoom_start=3)
        marker_cluster = MarkerCluster().add_to(map)

        pos = 0
        for point in coordinates:
            folium.Marker(point, popup=all_locations[pos], tooltip=all_locations[pos]).add_to(marker_cluster)
            pos += 1

        folium_static(map)

    def get_prepared_data(prepared_arr, pos):
        with open(prepared_arr[pos], 'r') as f:
            return f.readlines()

    def imdb_info(actors_names, all_locations, coordinates):
        draw_locations(coordinates, all_locations)


    oscar_data, best_picture_data, movie_metadata = get_data()

    '''
        # Финальный проект
    '''

    '''
        Использованные технологии:
        * обработка данных с помощью pandas
        * веб-скреппинг(Selenium)
        * работа с недокументированным API
        * визуализация(локации, актеры, простая гистограмма)
        * numpy(нормирование данных, преобразование колонок таблиц)
        * streamlit
        * регулярные выражения
        * геоданные(folium, geopy, pyvis)
        * машинное обучение
        * networkx
        * доп технологии: geopy и pyvis - преобразование адреса локации фильма в широту и долготу 
        * больше 120 строк)
    '''

    show_data = st.expander("Посмотреть данные")

    with show_data:
        st.write(oscar_data.head(20))
        st.write(best_picture_data.head(20))
        st.write(movie_metadata.head(20))

    """
        # Работа с сайтом IMDB
    """

    """
        ## Для начала возьмем популярные фильмы и сериалы сейчас(с помощью нужного API запроса) и посмотрим, какие жанры там встречаются 
    """

    # the following python code was collected from https://curlconverter.com/ using cURL link derived from IMDB
    # START FROM https://curlconverter.com/
    cookies = {
        'uu': 'eyJpZCI6InV1MTQ0OWM1ZDI1ZWE3NGMwMzg2OWQiLCJwcmVmZXJlbmNlcyI6eyJmaW5kX2luY2x1ZGVfYWR1bHQiOmZhbHNlfX0=',
        'ubid-main': '132-0172990-2453204',
        'session-id': '140-0676346-1587024',
        'adblk': 'adblk_no',
        'session-id-time': '2082787201l',
        'session-token': 'm5QQdqTyS46QzwOvxBabaVn1WH4nXGECR+DWAMfcxq4nX+3Q+EaixprdyKv79hoBsskn6iZB8f/Cmxwfnpz/qGAEJLG/9KC7yShPAQc/U5wu5hnPfgEHb+ZmKUD72FaWUJbtXnyZjipSgnzYzZJt1c5h9f3U5CrhDtGDA04HFDFBqvXyrJiy+qM0If/B5iGEHPglVTlwf2ZD8YdJ/W4SDg',
    }

    headers = {
        'authority': 'api.graphql.imdb.com',
        'accept': '*/*',
        'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'content-type': 'application/json',
        # Requests sorts cookies= alphabetically
        # 'cookie': 'uu=eyJpZCI6InV1MTQ0OWM1ZDI1ZWE3NGMwMzg2OWQiLCJwcmVmZXJlbmNlcyI6eyJmaW5kX2luY2x1ZGVfYWR1bHQiOmZhbHNlfX0=; ubid-main=132-0172990-2453204; session-id=140-0676346-1587024; adblk=adblk_no; session-id-time=2082787201l; session-token=m5QQdqTyS46QzwOvxBabaVn1WH4nXGECR+DWAMfcxq4nX+3Q+EaixprdyKv79hoBsskn6iZB8f/Cmxwfnpz/qGAEJLG/9KC7yShPAQc/U5wu5hnPfgEHb+ZmKUD72FaWUJbtXnyZjipSgnzYzZJt1c5h9f3U5CrhDtGDA04HFDFBqvXyrJiy+qM0If/B5iGEHPglVTlwf2ZD8YdJ/W4SDg',
        'origin': 'https://www.imdb.com',
        'referer': 'https://www.imdb.com/',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="102", "Google Chrome";v="102"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36',
        'x-amzn-sessionid': '140-0676346-1587024',
        'x-imdb-client-name': 'imdb-web-next',
        'x-imdb-user-country': 'RU',
        'x-imdb-user-language': 'ru-RU',
    }

    params = {
        'operationName': 'BatchPage_HomeMain',
        'variables': '{"fanPicksFirst":30,"topPicksFirst":30}',
        'extensions': '{"persistedQuery":{"sha256Hash":"43d7cd8f063ac6cb0784c3accec54e7fdb2fb95fcd83f63fc7022cc39f6acf85","version":1}}',
    }

    response = requests.get('https://api.graphql.imdb.com/', params=params, cookies=cookies, headers=headers)
    # END FROM

    found = response.json()
    fan_list = found["data"]["fanPicksTitles"]["edges"]
    movie_list = []
    movie_names = []
    for el in fan_list:
        genres = []
        for el1 in el["node"]["titleCardGenres"]["genres"]:
            genres.append(el1["text"])

        movie_list.append([el["node"]["originalTitleText"]["text"], genres])

    fan_fav = pd.DataFrame(movie_list, columns=["movie", "genres"])
    dct_count = {}
    for ind, row in fan_fav.iterrows():
        for el in row["genres"]:
            if (el in dct_count):
                dct_count[el] += 1
            else:
                dct_count[el] = 1

    res = pd.DataFrame(list(dct_count.items()), columns=["genre", "num"])
    fig = px.histogram(res, x="genre", y="num",
                       labels={"genre": "Жанр"})
    st.write(fan_fav)
    st.plotly_chart(fig)

    """
        ## Далее с помощью веб-скреппинга получим информацию по конкрентному фильму - список актеров и локации, где фильм был снят. 
        ## Код для обработки прописан в функциях выше, а также в отдельном файле .ipynb на гитхабе, где можно ввести любой фильм самому и получить те же данные.
    """

    '''
        ## Можно выбрать обработанные фильмы из предложенного списка
    '''

    movies_prepared = ["The ShawShank Redemption", "The Godfather", "The Dark Knight"]
    actors_prepared = ["TheShawShankRedemptionActors.txt","TheGodfatherActors.txt","TheDarkKnightActors.txt"]
    loc_prepared = ["TheShawShankRedemptionLoc.txt", "TheGodfatherLoc.txt", "TheDarkKnightLoc.txt"]
    coor_prepared = ["TheShawShankRedemptionCoor.txt","TheGodfatherCoor.txt", "TheDarkKnightCoor.txt"]

    picked_movie = st.selectbox("Выбрать фильм из списка для демонстрации", movies_prepared)
    pos = movies_prepared.index(picked_movie)
    actors_names = get_prepared_data(actors_prepared, pos)
    all_locations = get_prepared_data(loc_prepared, pos)
    coordinates = get_prepared_data(coor_prepared, pos)
    coordinates = [eval(x) for x in coordinates]

    '''
        ## Локации, где снимался фильм
    '''
    draw_locations(coordinates, all_locations)

    '''
        ## Интересно посмотреть, в каком количестве фильмов, которые были номинированы на Оскар, снялся любой актер
    '''

    picked_actor = st.selectbox("Выберете актера", actors_names)
    cnt_nominations = 0
    cnt_wins = 0
    for ind, movie in best_picture_data.dropna().iterrows():
        actors = [x.strip() for x in movie["Actors"].split(",")]
        if(picked_actor.strip() in actors):
            if(movie["Award"] == "Nominee"):
                cnt_nominations += 1
            else:
                cnt_wins += 1

    st.write("Номинированные фильмы: ", cnt_nominations)
    st.write("Фильмы с оскаром: ", cnt_wins)

    '''
        ## С кем этот актер снимался за свою актеру?
    '''

    try:
        actor_links = pd.DataFrame(columns=["from", "to"])

        for ind, movie in best_picture_data.dropna().iterrows():
            actors = [x.strip() for x in movie["Actors"].split(",")]
            if(picked_actor.strip() in actors):
                for other_actor in actors:
                    if(picked_actor.strip()!=other_actor):
                        actor_links = pd.concat([actor_links, pd.DataFrame({"from": [picked_actor.strip()], "to": [other_actor]})])

        graph = nx.DiGraph([(frm, to) for (frm, to) in actor_links.values])
        subgraph = graph.subgraph([picked_actor.strip()] + list(graph.neighbors(picked_actor.strip())))

        g = net.Network(height=500, width=500)
        g.from_nx(subgraph)
        g.show("vis.html")
        HtmlFile = open("vis.html", 'r', encoding='utf-8')
        source_code = HtmlFile.read()
        components.html(source_code, height=500, width=800)
    except nx.exception.NetworkXError:
        st.write("Этого актера нет в данных")

    '''
        ## Попробуем предсказать, соберет ли фильм 100 миллионов в прокате, используя наши данные
    '''

    st.write("Кодируем единицой те фильмы, которым удалось собрать 100 миллионов в прокате")

    df_copy = movie_metadata.copy().dropna()

    target = np.where(df_copy["gross"] <= 100000000, 0, 1)

    df = df_copy.loc[:,["duration", "budget","imdb_score"]]

    col1, col2 = st.columns(2)

    with col1:
        st.write(df.head(10))

    with col2:
        st.write(pd.DataFrame(target, columns = ["1 - собрал, 0 - нет"]).head(10))

    df = (df - df.mean())/df.std()

    X_train, X_test, y_train, y_test = train_test_split(df, target)

    knn = KNeighborsClassifier()
    knn.fit(X_train, y_train)
    y_pred = knn.predict(X_test)

    st.write("Модель готова")
    st.write("AUC SCORE: ", roc_auc_score(y_test, y_pred))

    st.write("Теперь эту простую модель можно попробовать использовать для фильмов, которые только вышли в прокат, и попытаться предсказать их сборы")

    '''
        ## И последнее, давайте вернемся к одному из трех наших фильмов, а именно фильму Темный Рыцарь(The Dark Knight) и посмотрим на все диалоги в этом фильме
    '''

    dialogues = pd.read_csv("joker.csv")
    s = ""
    for ind, row in dialogues.iterrows():
        s = s + row["line"]

    word = st.text_input("Введите слово: ")
    cnt = len(re.findall(word, s))
    st.write("Сколько раз слово встречается в фильме: ", cnt)

    st.write("Например, имя главного героя вообще не называется в фильме, слово джокер произносится только 4 раза")

    """
        # Спасибо за внимание
    """









