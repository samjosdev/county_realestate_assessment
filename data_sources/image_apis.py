import os
import requests
import random
import hashlib
from typing import List, Tuple
from dotenv import load_dotenv

load_dotenv()
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

def fetch_unsplash_image_urls(query, count=1, access_key=UNSPLASH_ACCESS_KEY):
    """Fetch image URLs from Unsplash API"""
    if not access_key:
        return []
    
    url = "https://api.unsplash.com/search/photos"
    params = {
        "query": query,
        "per_page": count,
        "orientation": "landscape"
    }
    headers = {"Authorization": f"Client-ID {access_key}"}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        images = [(img["id"], img["urls"]["regular"], "Unsplash") for img in results]
        return images
    except Exception:
        return []

def fetch_pexels_image_urls(query, count=1, api_key=PEXELS_API_KEY):
    """Fetch image URLs from Pexels API"""
    if not api_key:
        return []
    
    url = "https://api.pexels.com/v1/search"
    params = {
        "query": query,
        "per_page": count,
        "orientation": "landscape"
    }
    headers = {"Authorization": api_key}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        results = data.get("photos", [])
        images = [(img["id"], img["src"]["large"], "Pexels") for img in results]
        return images
    except Exception:
        return []

def fetch_wikipedia_images(county_name, state_name, count=3):
    """Fetch images from Wikipedia for a county"""
    try:
        # Clean county name
        county_clean = county_name.replace(" County", "").replace(" Parish", "")
        
        # Try different search patterns
        search_terms = [
            f"{county_clean} County, {state_name}",
            f"{county_clean}, {state_name}",
            f"{county_clean} County",
            f"{county_clean} {state_name}"
        ]
        
        images = []
        for term in search_terms:
            if len(images) >= count:
                break
                
            try:
                # Use Wikipedia API to search for pages
                search_url = "https://en.wikipedia.org/w/api.php"
                search_params = {
                    "action": "query",
                    "format": "json",
                    "list": "search",
                    "srsearch": term,
                    "srlimit": 1
                }
                
                search_response = requests.get(search_url, params=search_params, timeout=10)
                search_response.raise_for_status()
                search_data = search_response.json()
                
                if search_data.get("query", {}).get("search"):
                    page_id = search_data["query"]["search"][0]["pageid"]
                    
                    # Get images from the page
                    images_url = "https://en.wikipedia.org/w/api.php"
                    images_params = {
                        "action": "query",
                        "format": "json",
                        "prop": "images",
                        "pageids": page_id,
                        "imlimit": 10
                    }
                    
                    images_response = requests.get(images_url, params=images_params, timeout=10)
                    images_response.raise_for_status()
                    images_data = images_response.json()
                    
                    page_images = images_data.get("query", {}).get("pages", {}).get(str(page_id), {}).get("images", [])
                    
                    for img in page_images:
                        if len(images) >= count:
                            break
                            
                        img_title = img["title"]
                        if any(ext in img_title.lower() for ext in [".jpg", ".jpeg", ".png", ".gif"]):
                            # Get image info
                            info_url = "https://en.wikipedia.org/w/api.php"
                            info_params = {
                                "action": "query",
                                "format": "json",
                                "prop": "imageinfo",
                                "titles": img_title,
                                "iiprop": "url|size"
                            }
                            
                            info_response = requests.get(info_url, params=info_params, timeout=10)
                            info_response.raise_for_status()
                            info_data = info_response.json()
                            
                            pages = info_data.get("query", {}).get("pages", {})
                            for page_id, page_data in pages.items():
                                if page_id != "-1":  # Page exists
                                    imageinfo = page_data.get("imageinfo", [])
                                    if imageinfo:
                                        img_url = imageinfo[0]["url"]
                                        img_id = f"wiki_{page_id}"
                                        images.append((img_id, img_url, "Wikipedia"))
                                        break
                                        
            except requests.exceptions.RequestException:
                continue
                
        return images[:count]
    except Exception:
        return []

def fetch_serper_image_urls(query, count=3, api_key=None):
    """Fetch image URLs using Serper API (Google Images)"""
    if not api_key:
        return []
    
    url = "https://google.serper.dev/images"
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    payload = {"q": query, "num": count}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        images = data.get("images", [])
        return [(img.get("imageUrl", ""), img.get("imageUrl", ""), "Google Images") for img in images]
    except Exception:
        return []

def get_county_images(county_name, state_name, county_seat=None, used_urls=None):
    """Get images for a county from multiple sources, limited to 10 total"""
    seen_urls = set() if used_urls is None else set(used_urls)
    images = []
    county_clean = county_name.replace(" County", "").replace(" Parish", "")
    county_hash = hashlib.md5(f"{county_name}{state_name}".encode()).hexdigest()
    seed_offset = int(county_hash[:4], 16) % 1000
    queries = []
    
    if county_seat:
        queries.append(f"{county_seat} {county_clean} {state_name} downtown")
        queries.append(f"{county_seat} {county_clean} {state_name} main street")
        queries.append(f"{county_seat} {county_clean} {state_name} courthouse")
        queries.append(f"{county_seat} {county_clean} {state_name} aerial")
        queries.append(f"{county_seat} {county_clean} {state_name} landmarks")
    
    queries.extend([
        f"{county_clean} County {state_name}",
        f"{county_clean} {state_name}",
        f"{county_clean} County courthouse",
        f"{county_clean} County downtown",
        f"{county_clean} County aerial view"
    ])
    
    # Shuffle queries for variety
    random.seed(seed_offset)
    random.shuffle(queries)
    
    # Try Unsplash first
    for query in queries:
        if len(images) >= 10:
            break
        unsplash_images = fetch_unsplash_image_urls(query, 2)
        for img_id, img_url, source in unsplash_images:
            if img_url not in seen_urls and len(images) < 10:
                seen_urls.add(img_url)
                images.append((img_url, source))
    
    # Try Pexels
    for query in queries:
        if len(images) >= 10:
            break
        pexels_images = fetch_pexels_image_urls(query, 2)
        for img_id, img_url, source in pexels_images:
            if img_url not in seen_urls and len(images) < 10:
                seen_urls.add(img_url)
                images.append((img_url, source))
    
    # Try Wikipedia
    if len(images) < 10:
        wiki_images = fetch_wikipedia_images(county_name, state_name, 3)
        for img_id, img_url, source in wiki_images:
            if img_url not in seen_urls and len(images) < 10:
                seen_urls.add(img_url)
                images.append((img_url, source))
    
    # Update used_urls set
    if used_urls is not None:
        used_urls.update(seen_urls)
    
    return images[:10] 