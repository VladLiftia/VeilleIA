# Automatisation de Veille RSS avec Notation IA et Intégration Notion

Ce projet est un script d'automatisation en Python qui effectue une veille sur des flux RSS, utilise une intelligence artificielle (via l'API OpenAI) pour évaluer la pertinence des articles, et intègre les plus intéressants dans une base de données Notion.

## Fonctionnalités

- **Surveillance de flux RSS** : Récupère les derniers articles depuis une liste de flux RSS configurable.
- **Notation par IA** : Fait analyser le contenu de chaque article par un modèle de langage (GPT) pour lui attribuer une note de pertinence sur 20 selon des critères prédéfinis.
- **Filtrage intelligent** : Ne retient que les articles dépassant un seuil de notation (par défaut > 16/20).
- **Intégration à Notion** : Ajoute automatiquement les articles pertinents dans une base de données Notion.
- **Évite les doublons** : Garde une trace des articles déjà traités pour ne pas les ajouter plusieurs fois.

## Comment ça marche ?

1.  Le script charge la configuration depuis le fichier `.env` (clés d'API, ID de la base de données, etc.).
2.  Il lit la liste des articles déjà traités depuis `processed_articles.txt`.
3.  Il parcourt les flux RSS et récupère les articles qui n'ont pas encore été traités.
4.  Pour chaque nouvel article, il télécharge le contenu de la page web.
5.  Le contenu est envoyé à l'API OpenAI avec une instruction (prompt) pour obtenir une note sur 20.
6.  Si la note est supérieure à 14, l'article (titre, URL, note) est ajouté à la base de données Notion.
7.  L'URL de l'article est sauvegardée dans `processed_articles.txt` pour ne pas le traiter à nouveau.

## Prérequis

- Python 3.7 ou supérieur
- Un compte [OpenAI](https://platform.openai.com/) avec une clé d'API
- Un compte [Notion](https://www.notion.so/) avec une clé d'intégration et une base de données

## Installation et Configuration

**1. Clonez ou téléchargez ce projet**

**2. Installez les dépendances**

Ouvrez un terminal dans le dossier du projet et exécutez :
```bash
pip install -r requirements.txt
```

**3. Créez et configurez le fichier `.env`**

Créez un fichier nommé `.env` à la racine du projet et copiez-y le contenu suivant. Remplacez les valeurs d'exemple par vos propres informations.

```ini
# Remplacer par vos informations
NOTION_API_KEY="VOTRE_CLE_API_NOTION"
NOTION_DATABASE_ID="VOTRE_ID_DE_BASE_DE_DONNEES_NOTION"
OPENAI_API_KEY="VOTRE_CLE_API_OPENAI"

# Listes des flux RSS à surveiller (séparés par des virgules)
RSS_FEEDS="https://www.usine-digitale.fr/informatique/rss,https://www.journaldunet.com/web-tech/developpeur/rss/"
```

**4. Configurez votre base de données Notion**

- Créez une nouvelle base de données dans Notion.
- Assurez-vous qu'elle contient les **trois colonnes suivantes** avec les noms et types exacts :
    - `Titre` (Type : `Titre`)
    - `URL` (Type : `URL`)
    - `Note` (Type : `Nombre`)
- [Créez une intégration Notion](https://www.notion.so/my-integrations) pour obtenir votre `NOTION_API_KEY`.
- **Partagez** votre base de données avec l'intégration que vous venez de créer.
- Récupérez l'ID de votre base de données (`NOTION_DATABASE_ID`) à partir de son URL.

## Utilisation

Une fois la configuration terminée, lancez le script avec la commande suivante :

```bash
python main.py
```

Le script s'exécutera et affichera sa progression dans le terminal.

Pour une utilisation régulière, vous pouvez automatiser son exécution à l'aide d'un `cron job` (sur Linux/macOS) ou du Planificateur de tâches (sur Windows).
