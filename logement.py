import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import re

def leboncoin_slug(ville):
    return ville.lower().replace(" ", "-")

def scrape_annonces(ville_slug, transaction="ventes", limit=20):
    url = f"https://www.leboncoin.fr/recherche?category=9&locations={ville_slug}&real_estate_type={transaction}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return pd.DataFrame()  # retourne un DF vide en cas d’erreur

    soup = BeautifulSoup(response.text, "html.parser")
    cards = soup.find_all("li", {"data-qa-id": "aditem_container"}, limit=limit)

    annonces = []
    for card in cards:
        try:
            titre = card.find("p", {"data-qa-id": "aditem_title"}).text.strip()
            prix_txt = card.find("span", {"data-qa-id": "aditem_price"}).text.strip()
            prix = int(re.sub(r"[^\d]", "", prix_txt)) if prix_txt else 0
            ville = card.find("p", {"data-qa-id": "aditem_location"}).text.strip()
            lien = "https://www.leboncoin.fr" + card.find("a")["href"]
            infos = card.find("p", {"data-qa-id": "aditem_tags"}).text.strip()
            annonces.append({
                "titre": titre, "prix": prix, "infos": infos, "ville": ville, "lien": lien
            })
        except Exception as e:
            continue

    return pd.DataFrame(annonces)


def afficher_annonces(tab, ville, transaction, prix_min, prix_max, limit):
    slug = leboncoin_slug(ville)
    with tab:
        st.subheader(f"Annonces immobilières à {ville}")
        df = scrape_annonces(slug, transaction, limit)
        df = df[(df["prix"] >= prix_min) & (df["prix"] <= prix_max)]

        if df.empty:
            st.warning("Aucune annonce trouvée avec ces filtres.")
        else:
            m = folium.Map(location=[45.76, 4.84], zoom_start=12)
            marker_cluster = MarkerCluster().add_to(m)
            for _, row in df.iterrows():
                popup = f"""
                <strong>{row['titre']}</strong><br>
                💶 {row['prix']} €<br>
                📏 {row['infos']}<br>
                📍 {row['ville']}<br>
                🔗 <a href="{row['lien']}" target="_blank">Voir l'annonce</a>
                """
                folium.Marker(
                    location=[45.76, 4.84],  # Tu peux améliorer avec géocodage plus tard
                    popup=popup,
                    icon=folium.Icon(color="green", icon="home")
                ).add_to(marker_cluster)
            st_data = st_folium(m, width=700, height=500)
            st.dataframe(df[["titre", "prix", "infos", "ville", "lien"]])