import requests
import json
import re
from concurrent.futures import ThreadPoolExecutor

API_KEY = "89dc647004be44c785266ccd4d69576a"
catalog = []
seen_ids = set()

def clean_text(text):
    if not text:
        return ""
    # Nettoie les caractères de séparation de lignes problématiques (LS/PS)
    return re.sub(r'[\u2028\u2029]', ' ', text)

def parse_item(item, cat_type):
    tmdb_id = item["id"]
    title = item.get("title") or item.get("name") or "Titre inconnu"
    date_str = item.get("release_date") or item.get("first_air_date") or ""
    year = date_str[:4] if date_str else "N/A"
    
    # Détermination du type exact
    is_anime = (cat_type == "anime")
    is_tv = (cat_type == "tv") or is_anime
    final_type = "anime" if is_anime else ("tv" if is_tv else "movie")
    
    return {
        "type": final_type,
        "imdb_id": f"tmdb_{tmdb_id}",
        "tmdb_id_clean": tmdb_id,
        "title": clean_text(title),
        "year": year,
        "rating": round(item.get("vote_average", 0), 1),
        "poster": f"https://image.tmdb.org/t/p/w342{item['poster_path']}" if item.get("poster_path") else "",
        "overview": clean_text(item.get("overview", ""))
    }

def fetch_page(endpoint, params, cat_type):
    try:
        r = requests.get(f"https://api.themoviedb.org/3/{endpoint}", params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            results = []
            for item in data.get("results", []):
                key = f"{cat_type}_{item['id']}"
                if key not in seen_ids and item.get("poster_path"):
                    seen_ids.add(key)
                    results.append(parse_item(item, cat_type))
            return results
    except Exception:
        pass
    return []

def run_extraction():
    print("🚀 Démarrage de l'extraction maximale via TMDB...")
    tasks = []

    # 1. Extraction des Films (De 1960 à 2026 -> jusqu'à 20 pages par an)
    print("📋 Préparation des requêtes pour les Films...")
    for year in range(2026, 1960, -1):
        for page in range(1, 21):
            tasks.append(("discover/movie", {
                "api_key": API_KEY, "language": "fr-FR", "page": page,
                "primary_release_year": year, "sort_by": "popularity.desc"
            }, "movie"))

    # 2. Extraction des Séries (De 1980 à 2026 -> jusqu'à 20 pages par an)
    print("📋 Préparation des requêtes pour les Séries...")
    for year in range(2026, 1980, -1):
        for page in range(1, 21):
            tasks.append(("discover/tv", {
                "api_key": API_KEY, "language": "fr-FR", "page": page,
                "first_air_date_year": year, "sort_by": "popularity.desc"
            }, "tv"))

    # 3. Extraction de TOUS les Animés (Par genres et mots-clés -> 500 pages)
    print("📋 Préparation des requêtes pour les Animés...")
    for page in range(1, 501):
        tasks.append(("discover/tv", {
            "api_key": API_KEY, "language": "fr-FR", "page": page,
            "with_genres": "16", "with_original_language": "ja", "sort_by": "popularity.desc"
        }, "anime"))

    print(f"📦 Total de {len(tasks)} requêtes prêtes. Lancement du téléchargement...")

    # Traitement parallèle rapide (12 workers)
    completed = 0
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = [executor.submit(fetch_page, endpoint, params, cat_type) for endpoint, params, cat_type in tasks]
        
        for future in futures:
            res = future.result()
            catalog.extend(res)
            completed += 1
            if completed % 1000 == 0:
                print(f"🔄 Progression : {completed}/{len(tasks)} requêtes - {len(catalog)} contenus cumulés.")

    print(f"\n💾 Sauvegarde en cours dans data.json...")
    with open("data.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print(f"✅ Extrait avec succès ! {len(catalog)} contenus enregistrés dans data.json.")

if __name__ == "__main__":
    run_extraction()