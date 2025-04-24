import streamlit as st
import pandas as pd
import requests
from streamlit_option_menu import option_menu
import wikipedia
import urllib.parse
import re
from weather import display_weather_comparison, display_weather_comparison_forecast
from datetime import datetime
import folium
from streamlit_folium import st_folium
import json


# ----- CONFIGURATION DE LA PAGE -----
st.set_page_config(page_title="City Fighting", layout="wide")


# ----- CHARGER LES DONNÉES -----
data = pd.read_csv("data/data_commune.csv", delimiter=";")
donnees_comp = pd.read_csv("data/donnee_comp.csv", delimiter=";")
univ_data = pd.read_csv("data/univ.csv", delimiter=";", encoding="utf-8")

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
city1 = st.sidebar.selectbox("Ville 1", liste_villes, index=liste_villes.index("Bordeaux") if "Bordeaux" in liste_villes else 0)
city2 = st.sidebar.selectbox("Ville 2", liste_villes, index=liste_villes.index("Antibes") if "Antibes" in liste_villes else 1)

code_insee_city1 = data[data["LIBGEO"] == city1].iloc[0]["CODGEO"]
code_insee_city2 = data[data["LIBGEO"] == city2].iloc[0]["CODGEO"]


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

# Style CSS personnalisé pour les boîtes de KPI
st.markdown("""
<style>
:root {
    --kpi-primary: #6a11cb;
    --kpi-secondary: #2575fc;
    --kpi-accent: #ff5e62;
    --kpi-success: #38ef7d;
}

.kpi-box {
    border-radius: 15px;
    padding: 25px 20px;
    margin-bottom: 25px;
    background: linear-gradient(135deg, #f5f7fa 0%, #e4e8f0 100%);
    box-shadow: 0 6px 15px rgba(0,0,0,0.1);
    text-align: center;
    border-left: 5px solid var(--kpi-primary);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.kpi-box:hover {
    transform: translateY(-5px);
    box-shadow: 0 12px 20px rgba(0,0,0,0.15);
}

.kpi-title {
    font-size: 18px;
    color: #555;
    margin-bottom: 15px;
    font-weight: 600;
}

.kpi-value {
    font-size: 32px;
    font-weight: 700;
    background: linear-gradient(to right, var(--kpi-primary), var(--kpi-secondary));
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    margin: 10px 0;
}

.kpi-change-positive {
    color: var(--kpi-success);
    font-weight: bold;
}

.kpi-change-negative {
    color: var(--kpi-accent);
    font-weight: bold;
}

.kpi-source {
    font-size: 12px;
    color: #888;
    margin-top: 15px;
    font-style: italic;
}
</style>
""", unsafe_allow_html=True)

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
            st.subheader(city1)
            taux_chom1 = data1["P21_CHOM1564"] / data1["P21_ACT1564"] * 100
            taux_emp1 = (data1["P21_ACT1564"] - data1["P21_CHOM1564"]) / data1["P21_ACT1564"] * 100
            create_kpi_box("Taux de chômage", f"{taux_chom1:.1f} %")
            create_kpi_box("Taux d'emploi", f"{taux_emp1:.1f} %")

        with col2:
            st.subheader(city2)
            taux_chom2 = data2["P21_CHOM1564"] / data2["P21_ACT1564"] * 100
            taux_emp2 = (data2["P21_ACT1564"] - data2["P21_CHOM1564"]) / data2["P21_ACT1564"] * 100
            create_kpi_box("Taux de chômage", f"{taux_chom2:.1f} %")
            create_kpi_box("Taux d'emploi", f"{taux_emp2:.1f} %")

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

elif selected == "Données complémentaires":
    st.title("📍 Données complémentaires")
    st.subheader("Choisissez les entités à afficher sur la carte :")
    types_disponibles = donnees_comp["Type d'entité"].dropna().unique().tolist()
    if "Université" not in types_disponibles:
        types_disponibles.append("Université")

    types_choisis = st.multiselect("Types d'entités", types_disponibles)

    if types_choisis:
        col1, col2 = st.columns(2)

        if "Université" in types_choisis:
           def extract_universities(city):
                filt = univ_data["com_nom"].str.lower().str.strip() == city.lower().strip()
                df = univ_data[filt].copy()

                df = df[df["coordonnees"].str.contains(",", na=False)]
                
                # Séparation des coordonnées en latitude et longitude

                coords_split = df["coordonnees"].str.split(",", expand=True)
                if coords_split.shape[1] == 2:
                    df["lat"] = coords_split[0].astype(float)
                    df["lon"] = coords_split[1].astype(float)
                else:
                    df["lat"] = None
                    df["lon"] = None

                return df[["uo_lib", "lat", "lon"]].dropna(subset=["lat", "lon"])
              
                
                # df[["lat", "lon"]] = df["coordonnees"].str.split(",", expand=True).astype(float)

                # return df[["uo_lib", "lat", "lon"]].dropna()

        with col1:
            st.subheader(f"Universités à {city1}")
            univ_city1 = extract_universities(city1)
            if not univ_city1.empty:
                st.map(univ_city1)
            else:
                st.info("Aucune université trouvée pour cette ville.")

        with col2:
            st.subheader(f"Universités à {city2}")
            univ_city2 = extract_universities(city2)
            if not univ_city2.empty:
                st.map(univ_city2)
            else:
                st.info("Aucune université trouvée pour cette ville.")

        filtered_city1 = donnees_comp[(donnees_comp["Type d'entité"].isin(types_choisis)) & (donnees_comp["Commune"] == city1)]
        filtered_city2 = donnees_comp[(donnees_comp["Type d'entité"].isin(types_choisis)) & (donnees_comp["Commune"] == city2)]

        if "Université" not in types_choisis:  # afficher les autres cartes uniquement si Université non sélectionnée seule
            with col1:
                st.subheader(f"Carte pour {city1}")
                if not filtered_city1.empty:
                    map_city1 = filtered_city1.rename(columns={"LAT": "lat", "LONG": "lon"})[["lat", "lon"]]
                    st.map(univ_city1[["lat", "lon"]])
                    st.dataframe(univ_city1[["uo_lib", "lat", "lon"]].reset_index(drop=True))

                else:
                    st.info("Aucune entité trouvée pour cette ville.")

            with col2:
                st.subheader(f"Carte pour {city2}")
                if not filtered_city2.empty:
                    map_city2 = filtered_city2.rename(columns={"LAT": "lat", "LONG": "lon"})[["lat", "lon"]]
                    st.map(univ_city2[["lat", "lon"]])
                    st.dataframe(univ_city2[["uo_lib", "lat", "lon"]].reset_index(drop=True))

                else:
                    st.info("Aucune entité trouvée pour cette ville.")
    else:
        st.info("Veuillez sélectionner au moins un type d'entité à afficher.")

# ----- FOOTER OU INFO -----
st.markdown("---")
st.markdown("Application City Fighting - par Meriam Boumediene et Precy Gassai Lepoma")
