import streamlit as st
import pandas as pd
import requests
from streamlit_option_menu import option_menu
import wikipedia
import urllib.parse
import re
from weather import display_weather_comparison, display_weather_comparison_forecast


# ----- CONFIGURATION DE LA PAGE -----
st.set_page_config(page_title="City Fighting", layout="wide")


# ----- CHARGER LES DONNÉES -----
data = pd.read_csv("data_commune.csv", delimiter=";")

liste_villes = [str(ville) for ville in data["LIBGEO"] if isinstance(ville, str) and ville.strip()]

# Tri alphabétique
liste_villes = sorted(liste_villes)

# ----- SIDEBAR -----
st.sidebar.title("Comparateur de villes")
city1 = st.sidebar.selectbox("Ville 1", liste_villes, index=liste_villes.index(" ") if " " in liste_villes else 0)
city2 = st.sidebar.selectbox("Ville 2", liste_villes, index=liste_villes.index(" ") if " " in liste_villes else 1)


with st.sidebar:
    selected = option_menu(
        menu_title="Choisissez une catégorie",
        options=["Données générales", "Emploi", "Logement", "Météo", "Données complémentaires"],
        icons=["bar-chart", "briefcase", "house", "cloud-sun", "map"],
        menu_icon="cast",
        default_index=0,
        orientation="vertical"
    )

# ----- FONCTIONS UTILITAIRES -----
wikipedia.set_lang("fr")

def get_city_summary(city_name):
    try:
        summary = wikipedia.summary(city_name, sentences=3)
        return summary
    except wikipedia.exceptions.DisambiguationError as e:
        return f"Page ambiguë pour {city_name} : {e.options[:3]}"
    except wikipedia.exceptions.PageError:
        return f"Aucune page trouvée pour {city_name}."
    except Exception as e:
        return f"Erreur : {str(e)}"
    

def get_blason_et_site_via_api(ville):
    ville_url = urllib.parse.quote(ville.replace(" ", "_"))
    api_url = f"https://fr.wikipedia.org/w/api.php"
    
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "format": "json",
        "titles": ville
    }

    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(api_url, params=params, headers=headers)
    data = response.json()

    pages = data["query"]["pages"]
    page = next(iter(pages.values()))

    
    if "revisions" not in page:
        return None

    content = page["revisions"][0]["slots"]["main"]["*"]

    # Regex pour le blason
    blason_match = re.search(r"\|\s*blason\s*=\s*(.+)", content)
    blason = blason_match.group(1).strip() if blason_match else None

    # Regex pour le site web
    site_match = re.search(r"\|\s*siteweb\s*=\s*(.+)", content)
    siteweb = site_match.group(1).strip() if site_match else None

    population_match = re.search(r"\|\s*population\s*=\s*(\d[\d\s]*\d)", content)
    population = population_match.group(1).strip() if population_match else None

    # Reconstruire l'URL du blason s’il est sur Wikimedia
    if blason and not blason.startswith("http"):
        blason_filename = blason.replace(" ", "_")
        blason_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{urllib.parse.quote(blason_filename)}"
    else:
        blason_url = blason

    return {
        "ville": ville,
        "blason_url": blason_url,
        "site_web": siteweb
    }


def display_general_data(city1, city2):
    st.subheader("🏙️ Présentation et comparaison des villes")

    data1 = data[data["LIBGEO"] == city1].iloc[0]
    data2 = data[data["LIBGEO"] == city2].iloc[0]

    tabs = st.tabs(["🧾 Informations", "👥 Population", "📐 Superficie & Densité", "🗺️ Carte"])

    with tabs[0]:
        col1, col2 = st.columns(2)
        for col, city, d in zip([col1, col2], [city1, city2], [data1, data2]):
            col.markdown(f"### 📍 {city}")
            info = get_blason_et_site_via_api(city)
            if info.get("blason_url"): col.image(info["blason_url"], width=120)
            if info.get("site_web"): col.markdown(f"🌐 [Site officiel]({info['site_web']})")
            col.markdown(get_city_summary(city))

    with tabs[1]:
        st.markdown("### 👥 Population")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Population 2015", int(data1["P15_POP"]))
            st.metric("Population 2021", int(data1["P21_POP"]))
            change1 = (data1["P21_POP"] - data1["P15_POP"]) / data1["P15_POP"] * 100
            st.metric("Évolution 2015-2021", f"{change1:.1f} %")
        with col2:
            st.metric("Population 2015", int(data2["P15_POP"]))
            st.metric("Population 2021", int(data2["P21_POP"]))
            change2 = (data2["P21_POP"] - data2["P15_POP"]) / data2["P15_POP"] * 100
            st.metric("Évolution 2015-2021", f"{change2:.1f} %")

    with tabs[2]:
        st.markdown("### 📐 Superficie & Densité")
        col1, col2 = st.columns(2)
        try:
            superf1 = float(data1["SUPERF"])
            pop1 = float(data1["P21_POP"])
            dens1 = pop1 / superf1
            col1.metric("Superficie (km²)", f"{superf1:.2f}")
            col1.metric("Densité (hab/km²)", f"{dens1:.2f}")
        except Exception:
            col1.warning("Données invalides pour la ville 1")

        try:
            superf2 = float(data2["SUPERF"])
            pop2 = float(data2["P21_POP"])
            dens2 = pop2 / superf2
            col2.metric("Superficie (km²)", f"{superf2:.2f}")
            col2.metric("Densité (hab/km²)", f"{dens2:.2f}")
        except Exception:
            col2.warning("Données invalides pour la ville 2")

    with tabs[3]:
        st.markdown("### 🗺️ Carte de localisation")
        coords1 = pd.DataFrame({"lat": [data1["LAT"]], "lon": [data1["LONG"]]})
        coords2 = pd.DataFrame({"lat": [data2["LAT"]], "lon": [data2["LONG"]]})
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(city1)
            st.map(coords1)
        with col2:
            st.subheader(city2)
            st.map(coords2)


# def get_city_coordinates(city, weather_api_key):
#     base_url = "http://api.openweathermap.org/geo/1.0/direct?q="
#     complete_url = base_url + city + ",FR&limit=1" + "&appid=" + weather_api_key
#     response = requests.get(complete_url)
#     return response.json()

# def get_weather_data_by_coords(lat, lon, weather_api_key):
#     base_url = "https://api.openweathermap.org/data/2.5/weather?"
#     complete_url = base_url + f"lat={lat}&lon={lon}&units=metric&lang=fr&appid={weather_api_key}"
#     response = requests.get(complete_url)
#     return response.json()

# def get_image_url(data):
#     iconid = data['weather'][0]['icon']
#     base_url = f"https://openweathermap.org/img/wn/{iconid}@2x.png"
#     return base_url

def display_comparison(dict1, dict2):
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(city1)
        for key, val in dict1.items():
            st.write(f"**{key}**: {val}")
    with col2:
        st.subheader(city2)
        for key, val in dict2.items():
            st.write(f"**{key}**: {val}")


def display_maps():
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(f"Carte pour {city1}")
        st.map()
    with col2:
        st.subheader(f"Carte pour {city2}")
        st.map()
    
# def display_accueil(city1, city2):
#     col1, col2 = st.columns(2)
#     with col1:
#         data = get_blason_et_site_via_api(city1)
#         if not data:
#             st.error(f"Impossible de récupérer les données pour {city1}")
#             return

#         st.subheader(f"{data['ville']}")
#         if data['blason_url']:
#             st.image(data['blason_url'], caption=f"Blason de {data['ville']}", width=200)
#         else:
#             st.warning("Pas de blason trouvé.")
#         if data['site_web']:
#             st.markdown(f"🌐 [Site officiel]({data['site_web']})")
#         else:
#             st.info("Site officiel non renseigné.")

#         data1=get_city_summary(city1)
#         st.write(data1)
#     with col2:
#         data = get_blason_et_site_via_api(city2)
#         if not data:
#             st.error(f"Impossible de récupérer les données pour {city2}")
#             return

#         st.subheader(f"{data['ville']}")
#         if data['blason_url']:
#             st.image(data['blason_url'], caption=f"Blason de {data['ville']}", width=200)
#         else:
#             st.warning("Pas de blason trouvé.")
#         if data['site_web']:
#             st.markdown(f"🌐 [Site officiel]({data['site_web']})")
#         else:
#             st.info("Site officiel non renseigné.")
        
#         data2=get_city_summary(city2)
#         st.write(data2)

# ----- AFFICHAGE PAR ONGLET -----

if selected == "Données générales":
    st.title("📊 Données générales")
    display_general_data(city1, city2)
    #display_accueil(city1, city2)

elif selected == "Emploi":
    st.title("💼 Emploi")
    tab1, tab2 = st.tabs(["📊 KPI", "🔍 Recherche"])
    data1 = data[data["LIBGEO"] == city1].iloc[0]
    data2 = data[data["LIBGEO"] == city2].iloc[0]
    with tab1:
        st.subheader("Indicateurs Clés de l'Emploi")
        col1, col2 = st.columns(2)
        with col1:
            taux_chom1 = data1["P21_CHOM1564"] / data1["P21_ACT1564"] * 100
            taux_emp1 = (data1["P21_ACT1564"] - data1["P21_CHOM1564"]) / data1["P21_ACT1564"] * 100
            st.metric(f"Taux de chômage - {city1}", f"{taux_chom1:.1f} %")
            st.metric(f"Taux d'emploi - {city1}", f"{taux_emp1:.1f} %")
        with col2:
            taux_chom2 = data2["P21_CHOM1564"] / data2["P21_ACT1564"] * 100
            taux_emp2 = (data2["P21_ACT1564"] - data2["P21_CHOM1564"]) / data2["P21_ACT1564"] * 100
            st.metric(f"Taux de chômage - {city2}", f"{taux_chom2:.1f} %")
            st.metric(f"Taux d'emploi - {city2}", f"{taux_emp2:.1f} %")
    with tab2:
        st.subheader("Recherche d'offres d'emploi")
        st.info("Intégration future d'une API comme Pôle Emploi.")
        st.text_input("🔎 Entrez un métier ou un secteur", "")
        st.button("Lancer la recherche")



elif selected == "Logement":
    st.title("🏠 Logement")
    tab1, tab2 = st.tabs(["📊 KPI", "🔍 Recherche"])
    data1 = data[data["LIBGEO"] == city1].iloc[0]
    data2 = data[data["LIBGEO"] == city2].iloc[0]
    with tab1:
        st.subheader("Indicateurs Clés du Logement")
        col1, col2 = st.columns(2)
        with col1:
            st.metric(f"Logements en 2021 - {city1}", int(data1["P21_LOG"]))
            st.metric(f"Résidences principales - {city1}", int(data1["P21_RP"]))
        with col2:
            st.metric(f"Logements en 2021 - {city2}", int(data2["P21_LOG"]))
            st.metric(f"Résidences principales - {city2}", int(data2["P21_RP"]))
    with tab2:
        st.subheader("Recherche de logement")
        st.info("Intégration future d'une API comme SeLoger ou INSEE Logement.")
        st.text_input("🔎 Entrez un type de logement ou une fourchette de prix", "")
        st.button("Rechercher")


elif selected == "Météo":
    st.title("🌦️ Météo")
    onglet1, onglet2 = st.tabs(["Aujourd'hui", "Demain"])

    with onglet1:
        weather_api_key= st.secrets["weather_api_key"]
        # Appel de la fonction pour afficher les prévisions météorologiques
        col1, col2 = st.columns(2)
        with col1:
            st.html('<a href="https://www.prevision-meteo.ch/meteo/localite/aast"><img src="https://www.prevision-meteo.ch/uploads/widget/aast_0.png" width="650" height="250" /></a>')
        with col2:
            st.html('<a href="https://www.prevision-meteo.ch/meteo/localite/abainville"><img src="https://www.prevision-meteo.ch/uploads/widget/abainville_0.png" width="650" height="250" /></a>')
        display_weather_comparison(city1, city2, weather_api_key)
    
    with onglet2:
        weather_api_key= st.secrets["weather_api_key"]
        # Appel de la fonction pour afficher les prévisions météorologiques
        col1, col2 = st.columns(2)
        with col1:
            st.html('<a href="https://www.prevision-meteo.ch/meteo/localite/aast"><img src="https://www.prevision-meteo.ch/uploads/widget/aast_1.png" width="650" height="250" /></a>')
        with col2:
            st.html('<a href="https://www.prevision-meteo.ch/meteo/localite/abainville"><img src="https://www.prevision-meteo.ch/uploads/widget/abainville_1.png" width="650" height="250" /></a>')
        display_weather_comparison_forecast(city1, city2, weather_api_key)

elif selected == "Données complémentaires":
    st.title("📍 Données complémentaires")

    st.subheader("Choisissez ce que vous souhaitez afficher sur la carte :")
    lieux = st.multiselect(
        "Types de lieux à afficher",
        ["Musées", "Monuments", "Universités", "Hôpitaux", "Mairies"]
    )

    if lieux:
        st.success(f"Vous avez sélectionné : {', '.join(lieux)}")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"Carte pour {city1}")
            st.map()  # À remplacer par la carte réelle pour city1
        with col2:
            st.subheader(f"Carte pour {city2}")
            st.map()  # À remplacer par la carte réelle pour city2
    else:
        st.info("Veuillez sélectionner un ou plusieurs types de lieux dans la liste ci-dessus.")

# ----- FOOTER OU INFO -----
st.markdown("---")
st.markdown("Application City Fighting - Données publiques ©")