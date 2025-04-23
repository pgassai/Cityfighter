import requests
import streamlit as st
from datetime import datetime, timedelta

def get_city_coordinates(city, weather_api_key):
    base_url = "http://api.openweathermap.org/geo/1.0/direct"
    complete_url = f"{base_url}?q={city},FR&limit=1&appid={weather_api_key}"
    response = requests.get(complete_url)
    return response.json()

def get_weather_data_by_coords(lat, lon, weather_api_key):
    base_url = "https://api.openweathermap.org/data/2.5/weather"
    complete_url = f"{base_url}?lat={lat}&lon={lon}&units=metric&lang=fr&appid={weather_api_key}"
    response = requests.get(complete_url)
    return response.json()

def get_image_url(data):
    iconid = data['weather'][0]['icon']
    return f"https://openweathermap.org/img/wn/{iconid}@2x.png"


def display_weather_comparison(city1, city2, api_key):
    with st.spinner("Chargement des données météo..."):
        coords1 = get_city_coordinates(city1, api_key)
        coords2 = get_city_coordinates(city2, api_key)

        if coords1 and coords2:
            data1 = get_weather_data_by_coords(coords1[0]["lat"], coords1[0]["lon"], api_key)
            data2 = get_weather_data_by_coords(coords2[0]["lat"], coords2[0]["lon"], api_key)

            if data1.get("cod") != 404 and data2.get("cod") != 404:
                col1, col2 = st.columns(2)

                with col1:
                    #st.html('<a href="https://www.prevision-meteo.ch/meteo/localite/aast"><img src="https://www.prevision-meteo.ch/uploads/widget/aast_0.png" width="650" height="250" /></a>')
                    st.metric("Température moyenne", f"{data1['main']['temp']} °C")
                    st.metric("Humidité", f"{data1['main']['humidity']} %")
                    st.metric("Pression", f"{data1['main']['pressure']} hPa")
                    st.metric("Vent", f"{data1['wind']['speed']} m/s")
                    
                with col2:
                    #st.html('<a href="https://www.prevision-meteo.ch/meteo/localite/abainville"><img src="https://www.prevision-meteo.ch/uploads/widget/abainville_0.png" width="650" height="250" /></a>')
                    st.metric("Température moyenne", f"{data2['main']['temp']} °C")
                    st.metric("Humidité", f"{data2['main']['humidity']} %")
                    st.metric("Pression", f"{data2['main']['pressure']} hPa")
                    st.metric("Vent", f"{data2['wind']['speed']} m/s")
                    
            else:
                st.error("Impossible de récupérer les données météo pour une ou deux villes.")
        else:
            st.error("Ville non trouvée.")


#données méteo pour demain 
def get_weather_forecast_by_coords(lat, lon, weather_api_key):
    base_url = "https://api.openweathermap.org/data/2.5/forecast"
    complete_url = f"{base_url}?lat={lat}&lon={lon}&units=metric&lang=fr&appid={weather_api_key}"
    response = requests.get(complete_url)
    return response.json()

def get_forecast_for_tomorrow(forecast_data):
    tomorrow = datetime.now() + timedelta(days=1)
    target_time = tomorrow.strftime("%Y-%m-%d 12:00:00")

    for entry in forecast_data.get("list", []):
        if entry["dt_txt"] == target_time:
            return entry
    return None

def display_weather_comparison_forecast(city1, city2, api_key):
    with st.spinner("Chargement des prévisions météo (demain)..."):
        coords1 = get_city_coordinates(city1, api_key)
        coords2 = get_city_coordinates(city2, api_key)

        if coords1 and coords2:
            forecast1 = get_weather_forecast_by_coords(coords1[0]["lat"], coords1[0]["lon"], api_key)
            forecast2 = get_weather_forecast_by_coords(coords2[0]["lat"], coords2[0]["lon"], api_key)

            data1 = get_forecast_for_tomorrow(forecast1)
            data2 = get_forecast_for_tomorrow(forecast2)

            if data1 and data2:
                col1, col2 = st.columns(2)

                with col1:
                    st.metric("Température prévue", f"{data1['main']['temp']} °C")
                    st.metric("Humidité", f"{data1['main']['humidity']} %")
                    st.metric("Pression", f"{data1['main']['pressure']} hPa")
                    st.metric("Vent", f"{data1['wind']['speed']} m/s")

                with col2:
                    st.metric("Température prévue", f"{data2['main']['temp']} °C")
                    st.metric("Humidité", f"{data2['main']['humidity']} %")
                    st.metric("Pression", f"{data2['main']['pressure']} hPa")
                    st.metric("Vent", f"{data2['wind']['speed']} m/s")
            else:
                st.error("Impossible de récupérer les prévisions météo pour demain.")
        else:
            st.error("Ville non trouvée.")