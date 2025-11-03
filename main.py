import os
import feedparser
from newspaper import Article
import openai
from notion_client import Client
from dotenv import load_dotenv
import nltk
import time
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Télécharger les données NLTK nécessaires pour newspaper3k
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

PROCESSED_ARTICLES_FILE = 'processed_articles.txt'

def load_opml_feeds(opml_file):
    """Charge les flux RSS depuis un fichier OPML."""
    feeds = []
    try:
        if not os.path.exists(opml_file):
            print(f"⚠️ Fichier OPML '{opml_file}' non trouvé")
            return feeds
        
        tree = ET.parse(opml_file)
        root = tree.getroot()
        
        # Chercher tous les éléments <outline> avec un attribut xmlUrl
        for outline in root.iter('outline'):
            feed_url = outline.get('xmlUrl')
            feed_title = outline.get('text') or outline.get('title')
            
            if feed_url:
                feeds.append({
                    'url': feed_url,
                    'title': feed_title or 'Sans titre'
                })
        
        print(f"✓ {len(feeds)} flux RSS chargés depuis {opml_file}")
        return feeds
        
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du fichier OPML : {e}")
        return feeds

def load_processed_articles(file_path):
    """Charge les URLs des articles déjà traités depuis un fichier."""
    if not os.path.exists(file_path):
        return set()
    with open(file_path, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())

def save_processed_article(file_path, url):
    """Sauvegarde l'URL d'un article traité dans un fichier."""
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(url + '\n')

def is_article_recent(entry, max_age_hours=24):
    """Vérifie si un article a moins de X heures."""
    try:
        # Essayer différents champs de date
        date_fields = ['published_parsed', 'updated_parsed', 'created_parsed']
        
        for field in date_fields:
            if hasattr(entry, field) and getattr(entry, field):
                article_time = datetime(*getattr(entry, field)[:6])
                current_time = datetime.now()
                age = current_time - article_time
                
                # Retourner True si l'article a moins de max_age_hours heures
                if age <= timedelta(hours=max_age_hours):
                    return True, age
                else:
                    return False, age
        
        # Si aucune date n'est trouvée, on considère l'article comme récent (par sécurité)
        return True, None
        
    except Exception as e:
        return True, None  # En cas d'erreur, on garde l'article

def fetch_rss_articles(feed_urls, processed_links, max_age_hours=24):
    """Récupère les nouveaux articles à partir d'une liste de flux RSS."""
    articles = []
    
    for feed_info in feed_urls:
        # Support pour format dict (OPML) ou string (manuel)
        if isinstance(feed_info, dict):
            url = feed_info['url']
            feed_title = feed_info.get('title', 'Sans titre')
        else:
            url = feed_info
            feed_title = url.split('/')[2] if '/' in url else url
        
        print(f"Lecture : {feed_title[:50]}")
        
        try:
            # Ajouter un User-Agent
            feedparser.USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            feed = feedparser.parse(url)
            
            # Vérifier si le flux est valide
            if feed.bozo and not feed.entries:
                print(f"  ⚠️ Flux invalide ou inaccessible")
                continue
            
            # Compteurs
            recent_count = 0
            
            # On ne traite que les 50 articles les plus récents de chaque flux
            for entry in feed.entries[:50]:
                link = entry.link if hasattr(entry, 'link') else None
                title = entry.title if hasattr(entry, 'title') else "Sans titre"
                
                if link and link not in processed_links:
                    # Vérifier si l'article est récent
                    is_recent, age = is_article_recent(entry, max_age_hours)
                    
                    if is_recent:
                        recent_count += 1
                        # Récupérer aussi le résumé/description du flux RSS si disponible
                        description = ""
                        if hasattr(entry, 'description'):
                            description = entry.description
                        elif hasattr(entry, 'summary'):
                            description = entry.summary
                        
                        articles.append({
                            'title': title, 
                            'link': link,
                            'rss_description': description,
                            'age': age,
                            'source': feed_title
                        })
            
            if recent_count > 0:
                print(f"  ✓ {recent_count} article(s) récent(s) (< {max_age_hours}h)")
        except Exception as e:
            print(f"  ❌ Erreur : {str(e)[:60]}")
    
    return articles

def get_article_content(url, rss_description=""):
    """Extrait le contenu textuel d'un article à partir de son URL en utilisant newspaper3k."""
    try:
        # Pour les articles qui ne viennent PAS de Google News RSS, extraction normale
        if 'news.google.com' not in url:
            article = Article(url, language='fr')
            article.download()
            article.parse()
            
            if article.text and len(article.text.strip()) >= 100:
                print(f"  ✓ Contenu extrait : {len(article.text)} caractères")
                return article.text
            else:
                print(f"  ⚠️ Contenu trop court ({len(article.text.strip()) if article.text else 0} caractères)")
        
        # Pour Google News RSS (qui ne fonctionne pas bien), utiliser la description
        if rss_description:
            soup = BeautifulSoup(rss_description, 'html.parser')
            clean_text = soup.get_text(separator=' ', strip=True)
            
            if len(clean_text) >= 100:
                print(f"  📰 Utilisation de la description RSS ({len(clean_text)} caractères)")
                return clean_text
            else:
                print(f"  ⚠️ Description RSS trop courte ({len(clean_text)} caractères)")
        
        print(f"  ⚠️ Impossible d'extraire le contenu")
        return None
        
    except Exception as e:
        print(f"  ❌ Erreur extraction : {str(e)[:60]}")
        
        # Fallback sur la description RSS
        if rss_description:
            try:
                soup = BeautifulSoup(rss_description, 'html.parser')
                clean_text = soup.get_text(separator=' ', strip=True)
                if len(clean_text) >= 100:
                    print(f"  📰 Fallback sur description RSS ({len(clean_text)} caractères)")
                    return clean_text
            except:
                pass
        
        return None

def get_ai_rating_and_summary(content, api_key):
    """Note un article et génère un résumé en utilisant l'API OpenAI."""
    if not content:
        return 0, ""
    
    openai.api_key = api_key
    
    prompt = f"""
Tu dois effectuer deux tâches pour cet article :

1. **NOTATION** : Évalue l'article sur 20 selon ces critères pondérés :
   - Pertinence pour une entreprise d'accompagnement en IA (impact business, régulatoire ou stratégique pour décideurs non techniques) - Coefficient 4
   - Impact financier/politique (levée >1 Md$, loi nationale/UE/US, adoption gouvernementale) - Coefficient 3
   - Originalité (nouvelle inédite ou reprise) - Coefficient 2
   - Clarté de la source (officielle/institutionnelle) - Coefficient 1

2. **RÉSUMÉ** : Rédige un résumé très concis en maximum 2 lignes (environ 150-200 caractères).

Contenu de l'article :
---
{content[:5000]}
---

Réponds EXACTEMENT dans ce format (sans aucun autre texte) :
NOTE: [nombre entre 0 et 20]
RÉSUMÉ: [ton résumé en 2 lignes maximum]
"""
    
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tu es un assistant expert qui évalue et résume des articles d'actualité IA/tech. Tu dois retourner uniquement la note et le résumé dans le format demandé."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=150
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Parser la réponse
        rating = 0
        summary = ""
        
        lines = response_text.split('\n')
        for line in lines:
            if line.startswith('NOTE:'):
                rating_text = line.replace('NOTE:', '').strip()
                rating = int(''.join(filter(str.isdigit, rating_text)))
                rating = min(rating, 20)  # Limiter à 20 maximum
            elif line.startswith('RÉSUMÉ:') or line.startswith('RESUME:'):
                summary = line.replace('RÉSUMÉ:', '').replace('RESUME:', '').strip()
        
        return rating, summary
        
    except Exception as e:
        print(f"  ❌ Erreur lors de la notation/résumé par l'IA : {e}")
        return 0, ""

def add_articles_to_notion(api_key, database_id, articles, min_rating=15, max_articles=20):
    """Ajoute les articles pertinents à une base de données Notion."""
    notion = Client(auth=api_key)
    
    # Filtrer les articles avec note >= min_rating
    articles_above_threshold = [a for a in articles if a.get('rating', 0) >= min_rating]
    
    # Trier par note décroissante et garder les N meilleurs
    articles_sorted = sorted(articles_above_threshold, key=lambda x: x.get('rating', 0), reverse=True)
    articles_to_add = articles_sorted[:max_articles]
    
    print(f"\n{'='*60}")
    print(f"📊 Filtrage : {len(articles_above_threshold)} articles avec note >= {min_rating}/20")
    print(f"🎯 Sélection : Top {len(articles_to_add)} articles les mieux notés")
    print(f"{'='*60}\n")

    added_count = 0
    for article in articles_to_add:
        try:
            # Préparer les propriétés
            properties = {
                "Titre": {"title": [{"text": {"content": article['title'][:2000]}}]},
                "URL": {"url": article['link']},
                "Note": {"number": article['rating']}
            }
            
            # Ajouter le résumé s'il existe
            if article.get('summary'):
                properties["Résumé"] = {
                    "rich_text": [{"text": {"content": article['summary'][:2000]}}]
                }
            
            notion.pages.create(
                parent={"database_id": database_id},
                properties=properties
            )
            
            print(f"  ✓ Article ajouté : '{article['title'][:60]}...' (Note: {article['rating']}/20)")
            if article.get('summary'):
                print(f"    📝 Résumé : {article['summary'][:80]}...")
            
            save_processed_article(PROCESSED_ARTICLES_FILE, article['link'])
            added_count += 1
            
            # Pause pour éviter de surcharger l'API Notion
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ❌ Erreur pour '{article['title'][:60]}...' : {e}")
    
    print(f"\n✅ {added_count}/{len(articles_to_add)} articles ajoutés avec succès")

def main():
    """Fonction principale pour orchestrer le processus."""
    print("\n" + "="*60)
    print("🤖 AUTOMATISATION DE VEILLE RSS VERS NOTION")
    print("="*60)
    print(f"📅 Exécution : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Charger les variables d'environnement
    notion_api_key = os.getenv("NOTION_API_KEY")
    notion_database_id = os.getenv("NOTION_DATABASE_ID")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    rss_feeds_str = os.getenv("RSS_FEEDS", "")
    opml_file = os.getenv("OPML_FILE", "")
    max_age_hours = int(os.getenv("MAX_AGE_HOURS", "24"))

    # Vérifier que toutes les variables sont présentes
    if not all([notion_api_key, notion_database_id, openai_api_key]):
        print("❌ ERREUR : Variables d'environnement manquantes")
        print("Veuillez configurer dans le fichier .env :")
        print("  - NOTION_API_KEY")
        print("  - NOTION_DATABASE_ID")
        print("  - OPENAI_API_KEY")
        print("  - RSS_FEEDS ou OPML_FILE (au moins un)")
        print("  - MAX_AGE_HOURS (optionnel, défaut: 24)")
        return

    if not rss_feeds_str and not opml_file:
        print("❌ ERREUR : Vous devez configurer RSS_FEEDS ou OPML_FILE dans le .env")
        return

    if "VOTRE_" in (notion_api_key + openai_api_key):
        print("❌ ERREUR : Veuillez remplacer les valeurs d'exemple dans .env")
        return

    # Charger les flux RSS depuis OPML ou depuis RSS_FEEDS
    rss_feeds = []
    
    if opml_file:
        print(f"📁 Chargement des flux depuis le fichier OPML : {opml_file}")
        rss_feeds = load_opml_feeds(opml_file)
    
    if rss_feeds_str:
        print(f"📝 Ajout des flux RSS manuels depuis .env")
        manual_feeds = [{'url': feed.strip(), 'title': feed.strip()} for feed in rss_feeds_str.split(',') if feed.strip()]
        rss_feeds.extend(manual_feeds)
    
    print(f"✓ Configuration chargée")
    print(f"✓ {len(rss_feeds)} flux RSS configurés au total")
    print(f"✓ Filtrage : articles de moins de {max_age_hours}h\n")

    # Charger les articles déjà traités
    processed_links = load_processed_articles(PROCESSED_ARTICLES_FILE)
    print(f"📝 {len(processed_links)} articles déjà traités\n")

    # Récupérer les articles depuis les flux RSS
    print("🔍 Récupération des articles depuis les flux RSS...")
    print(f"{'='*60}")
    new_articles = fetch_rss_articles(rss_feeds, processed_links, max_age_hours)
    print(f"{'='*60}")
    print(f"\n📰 {len(new_articles)} nouveaux articles récents trouvés\n")

    if not new_articles:
        print("✓ Aucun nouvel article à traiter.")
        print("\n" + "="*60)
        print("Processus terminé avec succès")
        print("="*60 + "\n")
        return

    # Traiter chaque article
    print("⚙️  Traitement, notation et résumé des articles...\n")
    processed_articles = []
    
    for i, article in enumerate(new_articles, 1):
        # Afficher l'âge de l'article si disponible
        age_display = ""
        if article.get('age'):
            hours = int(article['age'].total_seconds() / 3600)
            minutes = int((article['age'].total_seconds() % 3600) / 60)
            age_display = f" [{hours}h{minutes:02d}]" if hours > 0 else f" [{minutes}min]"
        
        print(f"[{i}/{len(new_articles)}]{age_display} {article['title'][:55]}...")
        
        # Extraire le contenu
        content = get_article_content(article['link'], article.get('rss_description', ''))
        article['content'] = content

        if article['content']:
            # Noter et résumer avec l'IA
            rating, summary = get_ai_rating_and_summary(article['content'], openai_api_key)
            article['rating'] = rating
            article['summary'] = summary
            
            emoji = "⭐" if rating > 14 else "📄"
            print(f"  {emoji} Note : {rating}/20")
            if summary:
                print(f"  📝 Résumé : {summary[:80]}...")
        else:
            article['rating'] = 0
            article['summary'] = ""
            print(f"  ⚠️ Contenu non extrait, note : 0/20")
        
        processed_articles.append(article)
        print()
        
        # Petite pause entre chaque appel API
        if i < len(new_articles):
            time.sleep(1)

    # Ajouter les articles pertinents à Notion
    add_articles_to_notion(notion_api_key, notion_database_id, processed_articles)

    print("\n" + "="*60)
    print("✅ Processus terminé avec succès")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()