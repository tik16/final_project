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




    '''
        # Анализ различных данных про фильмы 
    '''

    st.write("Для начала посмотрим на данные по кинопремии Оскар. Используем два датасета - "
             "информация про все номинации в каждый год, а также расширенную информацию по номинации \"Лучший фильм\"")

    oscar_data, best_picture_data, movie_metadata = get_data()

    show_data = st.expander("Посмотреть данные")

    with show_data:
        st.write(oscar_data.tail(20))
        st.write(best_picture_data.head(20))

    winner_pictures = best_picture_data.loc[best_picture_data["Award"] == "Winner", :]
    winners_without_nan = winner_pictures.loc[winner_pictures["Content Rating"].isna() == False]

    fig,ax = plt.subplots(figsize = (8,8))
    ax.hist(winners_without_nan["Content Rating"])
    st.pyplot(fig)

    """
        # Работа с сайтом IMDB
    """

    st.write("Для демонстрации можно взять уже обработанные фильмы из предложенного списка")
    st.write("Также можно самому ввести название любого фильма, немного подождать и также получить результаты")

    movies_prepared = ["The ShawShank Redemption", "The Godfather", "The Dark Knight"]
    actors_prepared = ["TheShawShankRedemptionActors.txt","TheGodfatherActors.txt","TheDarkKnightActors.txt"]
    loc_prepared = ["TheShawShankRedemptionLoc.txt", "TheGodfatherLoc.txt", "TheDarkKnightLoc.txt"]
    coor_prepared = ["TheShawShankRedemptionCoor.txt","TheGodfatherCoor.txt", "TheDarkKnightCoor.txt"]

    col1, col2 = st.columns(2)
    with col1:
        picked_movie = st.selectbox("Выбрать фильм из списка для демонстрации", movies_prepared)
        pos = movies_prepared.index(picked_movie)
        actors_names = get_prepared_data(actors_prepared, pos)
        all_locations = get_prepared_data(loc_prepared, pos)
        coordinates = get_prepared_data(coor_prepared, pos)
        coordinates = [eval(x) for x in coordinates]

    with col2:
        title = st.text_input('Movie title')
        if(title):
            res = get_film_data(title)
            actors_names = res[0]
            film_url = res[1]
            loc_info = get_locations(film_url)
            all_locations = loc_info[0]
            coordinates = loc_info[1]


    st.write("Локации, где снимался фильм")
    draw_locations(coordinates, all_locations)

    st.write("Интересно посмотреть, в каком количестве фильмов, которые были номинированы на Оскар, снялся этот актер")
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

    st.write("С кем этот актер снимался за свою актеру?")
    st.write("Будем использовать только данные из ")

    st.write(movie_metadata.head(20))
    actor_links = pd.DataFrame(columns=["from", "to"])
    '''for ind,row in movie_metadata.iterrows():
        actor1 = row["actor_1_name"]
        actor2 = row["actor_2_name"]
        actor3 = row["actor_3_name"]
        #st.write(pd.DataFrame.from_dict({"from": actor1, "to": actor2}))
        actor_links = pd.concat([actor_links, pd.DataFrame({"from": [actor1], "to": [actor2]})])
        actor_links = pd.concat([actor_links, pd.DataFrame({"from": [actor1], "to": [actor3]})])'''

    for ind, movie in best_picture_data.dropna().iterrows():
        actors = [x.strip() for x in movie["Actors"].split(",")]
        if(picked_actor.strip() in actors):
            for other_actor in actors:
                if(picked_actor.strip()!=other_actor):
                    actor_links = pd.concat([actor_links, pd.DataFrame({"from": [picked_actor.strip()], "to": [other_actor]})])

    st.write(actor_links)

    wikigraph = nx.DiGraph([(frm, to) for (frm, to) in actor_links.values])
    subgraph = wikigraph.subgraph(
        [picked_actor.strip()] + list(wikigraph.neighbors(picked_actor.strip())))

    fig, ax = plt.subplots()
    g = net.Network(height=500, width=500)
    g.from_nx(subgraph)
    g.show("vis.html")
    HtmlFile = open("vis.html", 'r', encoding='utf-8')
    source_code = HtmlFile.read()

    components.html(source_code, height=1500, width=800)

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
    #END FROM

    found = response.json()
    fan_list = found["data"]["fanPicksTitles"]["edges"]
    movie_list = []
    for el in fan_list:
        movie_list.append(el["node"]["originalTitleText"]["text"])
    #st.write(movie_list)










