import streamlit as st
import pandas as pd
import geopandas as gpd
import requests
from streamlit_option_menu import option_menu
import wikipedia
import urllib.parse
import re
from weather import display_weather_comparison, display_weather_comparison_forecast
from datetime import datetime
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import json
import plotly.express as px
from logement import afficher_annonces



# ----- CONFIGURATION DE LA PAGE -----
st.set_page_config(page_title="City Fighting", page_icon = ":crossed_swords:", layout="wide")


# ----- CHARGER LES DONNÉES -----
data = pd.read_csv("data/data_commune.csv", delimiter=";")
donnees_comp = pd.read_csv("data/mairie.csv", delimiter=";")
univ_data = pd.read_csv("data/univ.csv", delimiter=";", encoding="utf-8")
gare_data = pd.read_csv("data/gares.csv", delimiter=";")
tourism_data = pd.read_csv("data/tourisme.csv", delimiter=";")
hospitals_data = pd.read_csv("data/hospitals.csv", delimiter=";")

# Extraire les coordonnées (géopoint : "POINT (longitude latitude)")
hospitals_data['coordinates'] = hospitals_data['the_geom'].apply(lambda x: x.replace('POINT (', '').replace(')', '').split(' '))

# Convertir les coordonnées en latitude et longitude
hospitals_data['longitude'] = hospitals_data['coordinates'].apply(lambda x: float(x[0]))
hospitals_data['latitude'] = hospitals_data['coordinates'].apply(lambda x: float(x[1]))


#liste_villes = [str(ville) for ville in data["LIBGEO"] if isinstance(ville, str) and ville.strip()]
liste_villes = [
    str(row["LIBGEO"]) 
    for _, row in data.iterrows()
    if row["P21_POP"] > 20000 and isinstance(row["LIBGEO"], str) and row["LIBGEO"].strip()
]

# Tri alphabétique
liste_villes = sorted(liste_villes)

# ----- SIDEBAR -----
st.sidebar.title("Comparateur de villes")
city1 = st.sidebar.selectbox("Ville 1", liste_villes, index=liste_villes.index("Aix-en-Provence") if "Aix-en-Provence" in liste_villes else 0)
city2 = st.sidebar.selectbox("Ville 2", liste_villes, index=liste_villes.index("Lille") if "Lille" in liste_villes else 1)

code_insee_city1 = data[data["LIBGEO"] == city1].iloc[0]["CODGEO"]
code_insee_city2 = data[data["LIBGEO"] == city2].iloc[0]["CODGEO"]


with st.sidebar:
    selected = option_menu(
        menu_title="Choisissez une catégorie",
        options=["Accueil","Informations générales", "Emploi", "Logement", "Météo", "Informations complémentaires"],
        icons=["house","bar-chart", "briefcase", "house", "cloud-sun", "map"],
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

# Style CSS personnalisé pour les boîtes de KPI
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def create_kpi_box(title, value, source=None):
    """Crée une boîte KPI stylisée"""
    box = f"""
    <div class="kpi-box">
        <div class="kpi-title">{title}</div>
        <div class="kpi-value">{value}</div>
        {f'<div class="kpi-source">{source}</div>' if source else ''}
    </div>
    """
    st.markdown(box, unsafe_allow_html=True)

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
            st.subheader(city1)
            create_kpi_box("Population 2015", f"{int(data1['P15_POP']):,}".replace(",", " "))
            create_kpi_box("Population 2021", f"{int(data1['P21_POP']):,}".replace(",", " "))
            change1 = (data1["P21_POP"] - data1["P15_POP"]) / data1["P15_POP"] * 100
            create_kpi_box("Évolution 2015-2021", f"{change1:.1f} %")
        
        with col2:
            st.subheader(city2)
            create_kpi_box("Population 2015", f"{int(data2['P15_POP']):,}".replace(",", " "))
            create_kpi_box("Population 2021", f"{int(data2['P21_POP']):,}".replace(",", " "))
            change2 = (data2["P21_POP"] - data2["P15_POP"]) / data2["P15_POP"] * 100
            create_kpi_box("Évolution 2015-2021", f"{change2:.1f} %")

    # Onglet Superficie & Densité
    with tabs[2]:
        st.markdown("### 📐 Superficie & Densité")
        
        col1, col2 = st.columns(2)
        
      
        with col1:
            st.subheader(city1)
            superficie1 = float(str(data1['SUPERF']).replace(',', '.'))
            population1 = float(str(data1['P21_POP']).replace(',', '.'))  # si nécessaire
            dens1 = population1 / superficie1
            superficie = float(str(data1['SUPERF']).replace(',', '.'))
            create_kpi_box("Superficie (km²)", f"{superficie1:,.2f}".replace(",", " "))
            create_kpi_box("Densité (hab/km²)", f"{dens1:.2f}")

    
        with col2:
            st.subheader(city2)
            superficie2 = float(str(data2['SUPERF']).replace(',', '.'))
            population2 = float(str(data2['P21_POP']).replace(',', '.'))  # si nécessaire
            dens2 = population2 / superficie2
            create_kpi_box("Superficie (km²)", f"{superficie2:,.2f}".replace(",", " "))
            create_kpi_box("Densité (hab/km²)", f"{dens2:.2f}")

    
    with tabs[3]:
        st.markdown("### 🗺️ Carte de localisation")
        lat1 = float(str(data1["LAT"]).replace(",", "."))
        lon1 = float(str(data1["LONG"]).replace(",", "."))
        lat2 = float(str(data2["LAT"]).replace(",", "."))
        lon2 = float(str(data2["LONG"]).replace(",", "."))

        # Création des DataFrames
        coords1 = pd.DataFrame({"lat": [lat1], "lon": [lon1]})
        coords2 = pd.DataFrame({"lat": [lat2], "lon": [lon2]})
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(city1)
            m = folium.Map(location = coords1, zoom_start = 11)
            folium.Marker(location=coords1, tooltip=city1).add_to(m)
            st_folium(m, width='100%', height=500)

        with col2:
            st.subheader(city2)
            m = folium.Map(location = coords2, zoom_start = 11)
            folium.Marker(location=coords2, tooltip=city2).add_to(m)
            st_folium(m, width='100%', height=500)




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
    


def get_access_token(client_id, client_secret):
    url = "https://entreprise.pole-emploi.fr/connexion/oauth2/access_token?realm=/partenaire"
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "api_offresdemploiv2 o2dsoffre"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(url, data=payload, headers=headers)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        st.error("Erreur d'authentification : " + response.text)
        return None

# Fonction pour récupérer les offres avec tri
def fetch_offres(code_insee, keyword, limit, token, ordre="Plus récentes"):
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "commune": code_insee,
        "motsCles": keyword,
        "range": f"0-{limit - 1}"
    }
    response = requests.get(
        "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search",
        headers=headers, params=params
    )
    if response.status_code == 3000000:
        st.error(f"Erreur API ({code_insee}) : {response.status_code} - {response.text}")
        return []
    
    try:
        data = response.json()
    except requests.exceptions.JSONDecodeError:
        st.warning(f"⚠️ Aucun résultat pour le mot-clé '{keyword}' à {code_insee}.")
        return []

    # 3. Si l’API renvoie une réponse valide mais sans résultats
    offres = data.get("resultats", [])
    if not offres:
        st.info(f"ℹ️ Aucun poste trouvé à {code_insee} pour le mot-clé : **{keyword}**.")
        return []


    offres = data["resultats"]
    offres_sorted = sorted(
        offres,
        key=lambda x: datetime.strptime(x.get("dateCreation", "1900-01-01T00:00:00.000Z"), "%Y-%m-%dT%H:%M:%S.%fZ"),
        reverse=(ordre == "Plus récentes")
    )
    return offres_sorted

# Fonction pour afficher une offre stylisée
def render_offre(offre):
    intitule = offre.get("intitule", "Offre sans titre")
    entreprise = offre.get("entreprise", {}).get("nom", "N/A")
    lieu = offre.get("lieuTravail", {}).get("libelle", "N/A")
    date = offre.get("dateCreation", "N/A").split("T")[0]
    contrat = offre.get("typeContratLibelle", "N/A")
    salaire = offre.get("salaire", {}).get("libelle", "Non précisé")
    description = offre.get("description", "").split("\n")[0][:150] + "..."
    lien_offre = f"https://candidat.francetravail.fr/offres/recherche/detail/{offre.get('id', '')}"

    st.markdown(f"""
        <div style='border: 1px solid #ddd; border-radius: 10px; padding: 15px; margin-bottom: 20px; background-color: #f9f9f9;'>
            <h4 style='color: #333;'>{intitule}</h4>
            <p><strong>🏢 {entreprise}</strong> — {lieu}</p>
            <p><strong>📅</strong> {date} | <strong>📄</strong> {contrat} | <strong>💶</strong> {salaire}</p>
            <p>{description}</p>
            <a href="{lien_offre}" target="_blank" style='text-decoration: none;'>
                <button style='background-color:#4CAF50; color:white; padding:8px 16px; border:none; border-radius:5px;'>Voir l'offre</button>
            </a>
        </div>
    """, unsafe_allow_html=True)

# Identifiants API
client_id = "PAR_cityfighter_87822568bc2896de7af0df9770a1824feb4f21b9c5a7a8870251a64e88a2db4c"
client_secret = "820b9f6263d658d14b921e37a5c6a0f0f6e3705e4ade1c02372fd3927ef95625"


# ----- INTERFACE -----
if selected == "Accueil":
    # --- Bannière stylisée ---
    st.markdown("""
        <style>

            .intro-text {
                padding-top: 0px;
                margin-top: 0px;
                text-align: justify;
                font-size: 17px;
                line-height: 1.6;
            }

            .linkedin-box {
                display: flex;
                justify-content: center;
                gap: 40px;
                margin-top: 30px;
            }

            .linkedin-card {
                background-color: #f5f5f5;
                padding: 15px 20px;
                border-radius: 10px;
                text-align: center;
                box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                transition: 0.3s;
            }

            .linkedin-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 8px 18px rgba(0,0,0,0.1);
            }

            .linkedin-card a {
                text-decoration: none;
                font-weight: bold;
                color: #0072b1;
                font-size: 16px;
            }

            .linkedin-card p {
                margin-top: 8px;
                color: #444;
            }
        </style>


        <h1 style='text-align:center;'>🌍 Bienvenue sur <span style="color:#4c8bf5">City Fighter</span></h1>

        <div class='intro-text'>

        ### 🎯 Objectif du projet

        <strong>City Fighter</strong> est une application interactive de comparaison de villes françaises, pensée pour vous aider à faire des choix éclairés que ce soit pour **vivre**, **travailler**, **étudier** ou **investir** dans une commune.

        Que vous soyez un particulier en quête d'une nouvelle ville ou un professionnel souhaitant analyser des données locales, City Fighter vous donne un **aperçu visuel et quantitatif** de nombreuses dimensions d’une ville.

        ###  Pourquoi utiliser City Fighter ?

        - Comparer rapidement deux villes côte à côte
        - Accéder à des **indicateurs démographiques, économiques, sociaux, météorologiques**
        - Visualiser les cartes, blasons, universités et autres entités locales
        - Explorer des données en quelques clics, de manière simple et intuitive

        ###  Indicateurs disponibles dans l’application :

        - **Informations générales** : population, superficie, densité...
        - **Emploi** : taux de chômage, taux d’emploi, offres d’emploi en temps réel
        - **Logement** : nombre de logements, résidences principales...
        - **Météo** : prévisions météo comparées pour aujourd’hui et demain
        - **Informations complémentaires** : mairies, universités, points d’intérêt géolocalisés
                
       ###  Technologies utilisées
        Ce projet est développé en **Python** avec le framework **Streamlit**, et s’appuie sur des **bases de données et API publiques** comme :

        - Data gouv
        - INSEE
        - France Travail (anciennement Pôle Emploi)
        - Wikipédia
        - OpenMeteo
        - Universités françaises (data.gouv)
        - Prévision Météo

        👈 Utilisez le menu latéral pour commencer à comparer vos villes préférées !

        </div>

        <hr>

        <h3 style='text-align:center;'>👩‍💻 Créatrices du projet </h3>
        <p style='text-align:center;'>Liens vers linkedin</p>
        <div class='linkedin-box'>
            <div class='linkedin-card'>
                <a href='https://www.linkedin.com/in/precy-gassai-lepoma/' target='_blank'>Précy Gassai Lepoma</a>
                <p>Data Analyst chez OPCO 2i</p>
            </div>
            <div class='linkedin-card'>
                <a href='https://www.linkedin.com/in/meriam-boumediene-240b35264/' target='_blank'>Meriam Boumediene</a>
                <p>Data Analyst chez VWFS</p>
            </div>
        </div>
                
        """, unsafe_allow_html=True)


elif selected == "Informations générales":
    st.title("📊 Informations générales")
    display_general_data(city1, city2)
    #display_accueil(city1, city2)

elif selected == "Emploi":
    st.title("💼 Emploi")
    tab1, tab2 = st.tabs(["📊 KPI", "🔍 Recherche"])
    data1 = data[data["LIBGEO"] == city1].iloc[0]
    data2 = data[data["LIBGEO"] == city2].iloc[0]
    with tab1:
        st.subheader("Indicateurs Clés de l'Emploi")

        # Calculs
        taux_chom1 = data1["P21_CHOM1564"] / data1["P21_ACT1564"] * 100
        taux_emp1 = (data1["P21_ACT1564"] - data1["P21_CHOM1564"]) / data1["P21_ACT1564"] * 100

        taux_chom2 = data2["P21_CHOM1564"] / data2["P21_ACT1564"] * 100
        taux_emp2 = (data2["P21_ACT1564"] - data2["P21_CHOM1564"]) / data2["P21_ACT1564"] * 100

        col1, col2 = st.columns(2)
        with col1:
            # 📊 Graphe Comparatif - Taux de chômage
            df_chomage = pd.DataFrame({
                "Ville": [city1, city2],
                "Taux de chômage (%)": [taux_chom1, taux_chom2]
            })

            fig_chom = px.bar(
                df_chomage,
                x="Ville",
                y="Taux de chômage (%)",
                color="Ville",
                text="Taux de chômage (%)",
                color_discrete_sequence=["#4d8076", "#ffa17a"]
            )
            fig_chom.update_traces(texttemplate='%{text:.1f} %', textposition='outside')
            fig_chom.update_layout(title="Comparaison du Taux de Chômage", yaxis_range=[0, 100])
            st.plotly_chart(fig_chom, use_container_width=True)

        with col2:
            # 📊 Graphe Comparatif - Taux d'emploi
            df_emploi = pd.DataFrame({
                "Ville": [city1, city2],
                "Taux d'emploi (%)": [taux_emp1, taux_emp2]
            })
            
        

            fig_emploi = px.bar(
                df_emploi,
                x="Ville",
                y="Taux d'emploi (%)",
                color="Ville",
                text="Taux d'emploi (%)",
                color_discrete_sequence=["#4d8076", "#ffa17a"]
            )
            fig_emploi.update_traces(texttemplate='%{text:.1f} %', textposition='outside')
            fig_emploi.update_layout(title="Comparaison du Taux d'Emploi", yaxis_range=[0, 100])
            st.plotly_chart(fig_emploi, use_container_width=True)
    with tab2:
        st.subheader("Recherche d'offres d'emploi comparée")

        # Saisie utilisateur
        keyword = st.text_input("🔎 Entrez un métier ou un secteur")
        limit = st.slider("Nombre d'offres à afficher par ville", 1, 10, 5)

        # Un seul bouton avec un identifiant unique
        rechercher = st.button("Lancer la recherche")
        tri_ordre = st.selectbox("Trier les offres par", ["Plus récentes", "Moins récentes"])

        if rechercher or keyword == "":
            token = get_access_token(client_id, client_secret)
            if token:
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(f"### 🔵 Offres à {city1}")
                    offres_city1 = fetch_offres(code_insee_city1, keyword, limit, token, tri_ordre)
                    if offres_city1:
                        cols = st.columns(2)
                        for i, offre in enumerate(offres_city1):
                            with cols[i % 2]:
                                render_offre(offre)
                    else:
                        st.warning(f"Aucune offre trouvée pour {city1}.")

                with col2:
                    st.markdown(f"### 🟣 Offres à {city2}")
                    offres_city2 = fetch_offres(code_insee_city2, keyword, limit, token, tri_ordre)
                    if offres_city2:
                        cols = st.columns(2)
                        for i, offre in enumerate(offres_city2):
                            with cols[i % 2]:
                                render_offre(offre)
                    else:
                        st.warning(f"Aucune offre trouvée pour {city2}.")


elif selected == "Logement":
    st.title("🏠 Logement")
    tab1, tab2 = st.tabs(["📊 KPI", "🔍 Recherche"])
    data1 = data[data["LIBGEO"] == city1].iloc[0]
    data2 = data[data["LIBGEO"] == city2].iloc[0]
    with tab1:
        st.subheader("Indicateurs Clés du Logement")
        col1, col2 = st.columns(2)
        with col1:
            create_kpi_box("Logements en 2021", int(data1["P21_LOG"]))
            df_ville1 = pd.DataFrame({
            'Catégorie': ['Résidences principales', 'Autres logements'],
            'Valeur': [data1["P21_RP"], data1["P21_LOG"] - data1["P21_RP"]]
                })

            fig1 = px.pie(
                df_ville1,
                names='Catégorie',
                values='Valeur',
                color_discrete_sequence=["#00BFFF", "#E8E8E8"]
                )
            st.plotly_chart(fig1)
            

        with col2:
            create_kpi_box("Logements en 2021", int(data2["P21_LOG"]))
            df_ville2 = pd.DataFrame({
            'Catégorie': ['Résidences principales', 'Autres logements'],
            'Valeur': [data2["P21_RP"], data2["P21_LOG"] - data2["P21_RP"]]
                })

            fig2 = px.pie(
                df_ville2,
                names='Catégorie',
                values='Valeur',
                color_discrete_sequence=["#00BFFF", "#E8E8E8"]
                )
            st.plotly_chart(fig2)
    with tab2:
        st.subheader("Recherche de logement")
        col1, col2 = st.columns(2)
        with col1:
            type_bien = st.radio("Type de logement :", ["ventes", "locations"], horizontal=True)
        with col2:
            nb_annonces = st.slider("Nombre d’annonces :", 10, 50, 20)

        prix_min, prix_max = st.slider("Filtrer par prix (€)", 0, 2000000, (0, 1000000), step=10000)


        
        # ---------------- Affichage ----------------

elif selected == "Météo":
    st.title("🌦️ Météo")
    onglet1, onglet2 = st.tabs(["Aujourd'hui", "Demain"])
    city1_lower = city1.lower()
    city2_lower = city2.lower()

    with onglet1:
        weather_api_key= st.secrets["weather_api_key"]
        # Appel de la fonction pour afficher les prévisions météorologiques
        col1, col2 = st.columns(2)
        with col1:
            st.html(f'<a href="https://www.prevision-meteo.ch/meteo/localite/{city1_lower}"><img src="https://www.prevision-meteo.ch/uploads/widget/{city1_lower}_0.png" width="650" height="250" /></a>')
        with col2:
            st.html(f'<a href="https://www.prevision-meteo.ch/meteo/localite/{city2_lower}"><img src="https://www.prevision-meteo.ch/uploads/widget/{city2_lower}_0.png" width="650" height="250" /></a>')
        display_weather_comparison(city1, city2, weather_api_key)
    
    with onglet2:
        weather_api_key= st.secrets["weather_api_key"]
       
        # Appel de la fonction pour afficher les prévisions météorologiques
        col1, col2 = st.columns(2)
        with col1:
            st.html(f'<a href="https://www.prevision-meteo.ch/meteo/localite/{city1_lower}"><img src="https://www.prevision-meteo.ch/uploads/widget/{city1_lower}_1.png" width="650" height="250" /></a>')
        with col2:
            st.html(f'<a href="https://www.prevision-meteo.ch/meteo/localite/{city2_lower}"><img src="https://www.prevision-meteo.ch/uploads/widget/{city2_lower}_1.png" width="650" height="250" /></a>')
        display_weather_comparison_forecast(city1, city2, weather_api_key)

elif selected == "Informations complémentaires":
    st.title("📍 Informations complémentaires")
    st.subheader("Choisissez les entités à afficher sur la carte :")
    types_disponibles = donnees_comp["Type d'entité"].dropna().unique().tolist()
    # Ajouter les entités spéciales
    for ent in ["Université", "Mairie", "Gare", "Hôpital","Activités"]:
        if ent not in types_disponibles:
            types_disponibles.append(ent)

    types_choisis = st.multiselect("Types d'entités", types_disponibles)

    # Fonctions d'extraction
    def extract_universities(city):
        filt = univ_data["localisation"].str.lower().str.contains(city.lower(), na=False)
        return univ_data[filt][["LAT", "LONG", "uo_lib"]] \
            .rename(columns={"LAT": "lat", "LONG": "lon", "uo_lib": "name"})

    def extract_mairies(city):
        filt = (donnees_comp["Type d'entité"] == "Mairie") & \
               (donnees_comp["Commune"].str.lower().str.contains(city.lower(), na=False))
        return donnees_comp[filt][["LAT", "LONG", "Nom de l'entité"]] \
            .rename(columns={"LAT": "lat", "LONG": "lon", "Nom de l'entité": "name"})

    def extract_gares(city):
        filt = gare_data["COMMUNE"].str.lower().str.contains(city.lower(), na=False)
        return gare_data[filt][["LAT", "LONG", "LIBELLE"]] \
            .rename(columns={"LAT": "lat", "LONG": "lon", "LIBELLE": "name"})

    def extract_hospitals(city):
        # Filtrer les hôpitaux par ville
        filt = hospitals_data['addr-city'].str.lower().str.contains(city.lower(), na=False)
        df = hospitals_data[filt].copy()
        # Extraire coordonnées depuis the_geom (format WKT)
        coords = df['the_geom'].str.extract(r'POINT \(([0-9\.-]+) ([0-9\.-]+)\)')
        df['lon'] = coords[0].astype(float)
        df['lat'] = coords[1].astype(float)
        # Utiliser le nom officiel ou nom court
        df['entity_name'] = df['name'].fillna(df.get('official_name', ''))
        return df[['lat', 'lon', 'entity_name']].rename(columns={'entity_name': 'name'})

    def extract_tourism(city):
        # Convertir les coordonnées de string (avec virgule) en float
        df = tourism_data.copy()
        df['lat'] = df['LAT'].astype(str).str.replace(',', '.').astype(float)
        df['lon'] = df['LONG'].astype(str).str.replace(',', '.').astype(float)
        filt = df['Commune'].str.lower().str.contains(city.lower(), na=False)
        return df[filt][['lat', 'lon', 'Nom_du_POI']].rename(columns={'Nom_du_POI': 'name'})

    if types_choisis:
        col1, col2 = st.columns(2)
        # Carte de la première ville
        with col1:
            st.subheader(f"Entités à {city1}")
            loc1 = data[data["LIBGEO"] == city1].iloc[0]
            m1 = folium.Map(location=[loc1["LAT"], loc1["LONG"]], zoom_start=12)
            if "Université" in types_choisis:
                for _, row in extract_universities(city1).iterrows():
                    folium.Marker(
                        location=[row["lat"], row["lon"]],
                        tooltip=row['name'], popup=f"Université : {row['name']}",
                        icon=folium.Icon(color="blue", icon="university", prefix="fa")
                    ).add_to(m1)
            if "Mairie" in types_choisis:
                for _, row in extract_mairies(city1).iterrows():
                    folium.Marker(
                        location=[row["lat"], row["lon"]],
                        tooltip=row['name'], popup=f"Mairie : {row['name']}",
                        icon=folium.Icon(color="green", icon="building", prefix="fa")
                    ).add_to(m1)
            if "Gare" in types_choisis:
                for _, row in extract_gares(city1).iterrows():
                    folium.Marker(
                        location=[row["lat"], row["lon"]],
                        tooltip=row['name'], popup=f"Gare : {row['name']}",
                        icon=folium.Icon(color="red", icon="train", prefix="fa")
                    ).add_to(m1)
            if "Hôpital" in types_choisis:
                for _, row in extract_hospitals(city1).iterrows():
                    folium.Marker(
                        location=[row["lat"], row["lon"]],
                        tooltip=row['name'], popup=f"Hôpital : {row['name']}",
                        icon=folium.Icon(color="orange", icon="hospital", prefix="fa")
                    ).add_to(m1)
            if "Activités" in types_choisis:
                for _, row in extract_tourism(city1).iterrows():
                    folium.Marker(
                        [row['lat'], row['lon']], tooltip=row['name'], popup=row['name'],
                        icon=folium.Icon(color='purple', icon='camera', prefix='fa')
                    ).add_to(m1)
            st_folium(m1, width=600, height=400)

        # Carte de la deuxième ville
        with col2:
            st.subheader(f"Entités à {city2}")
            loc2 = data[data["LIBGEO"] == city2].iloc[0]
            m2 = folium.Map(location=[loc2["LAT"], loc2["LONG"]], zoom_start=12)
            if "Université" in types_choisis:
                for _, row in extract_universities(city2).iterrows():
                    folium.Marker(
                        location=[row["lat"], row["lon"]],
                        tooltip=row['name'], popup=f"Université : {row['name']}",
                        icon=folium.Icon(color="blue", icon="university", prefix="fa")
                    ).add_to(m2)
            if "Mairie" in types_choisis:
                for _, row in extract_mairies(city2).iterrows():
                    folium.Marker(
                        location=[row["lat"], row["lon"]],
                        tooltip=row['name'], popup=f"Mairie : {row['name']}",
                        icon=folium.Icon(color="green", icon="building", prefix="fa")
                    ).add_to(m2)
            if "Gare" in types_choisis:
                for _, row in extract_gares(city2).iterrows():
                    folium.Marker(
                        location=[row["lat"], row["lon"]],
                        tooltip=row['name'], popup=f"Gare : {row['name']}",
                        icon=folium.Icon(color="red", icon="train", prefix="fa")
                    ).add_to(m2)
            if "Hôpital" in types_choisis:
                for _, row in extract_hospitals(city2).iterrows():
                    folium.Marker(
                        location=[row["lat"], row["lon"]],
                        tooltip=row['name'], popup=f"Hôpital : {row['name']}",
                        icon=folium.Icon(color="orange", icon="hospital", prefix="fa")
                    ).add_to(m2)
            if "Activités" in types_choisis:
                for _, row in extract_tourism(city2).iterrows():
                    folium.Marker(
                        [row['lat'], row['lon']], tooltip=row['name'], popup=row['name'],
                        icon=folium.Icon(color='purple', icon='camera', prefix='fa')
                    ).add_to(m2)
            st_folium(m2, width=600, height=400)

        
    else:
        st.info("Veuillez sélectionner au moins un type d'entité à afficher.")



# ----- FOOTER OU INFO -----
st.markdown("---")
st.markdown("Application City Fighting - par Meriam Boumediene et Precy Gassai Lepoma")
