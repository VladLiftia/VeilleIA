# Chercher et activer le venv
if [ -f "venv/bin/activate" ]; then
    echo "✓ Environnement virtuel trouvé, activation..."
    source venv/bin/activate    ← ICI IL ACTIVE LE VENV
    echo "✓ venv activé"
fi
```

## 📺 Ce que vous verrez à l'exécution :
```
============================================================
🚀 VEILLE RSS AUTOMATIQUE VERS NOTION
============================================================

⏰ Lancement : 2024-11-03 15:30:00

✓ main.py trouvé
✓ Configuration .env trouvée
✓ Environnement virtuel trouvé, activation...
✓ venv activé                              ← LE VENV EST ACTIVÉ !

============================================================
📡 Lancement du processus de veille...
============================================================

🤖 AUTOMATISATION DE VEILLE RSS VERS NOTION
...
```

## 🤔 Vous avez peut-être un problème différent ?

Si vous voyez ce message :
```
⚠️  Aucun environnement virtuel trouvé
Le script va utiliser Python global