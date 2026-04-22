# Système de Quêtes HexaHold - Documentation

## Overview
Le système de quêtes offre une interface flexible et facile à utiliser pour gérer les quêtes dans le jeu. Les quêtes sont divisées en 3 sections : **Quotidiennes**, **Missions**, et **Événements**.

## Comment ajouter une quête

Ouvrez le fichier `quetes.py` et ajoutez votre quête dans le dictionnaire `QUETES` avec la structure suivante :

```python
"votre_quest_id": {
    "nom": "Nom affiché de la quête",
    "description": "Description courte visible au menu",
    "section": "quotidiennes" | "missions" | "evenements",
    "type_evenement": None | "histoire" | "guerre" | "infini",  # Pour section "evenements"
    "xp": 10,              # Points d'XP gagnés à la complétionl
    "pieces": 50,          # Pièces gagnées à la complétio
    "gemmes": 0,           # Gemmes gagnées à la complétionl
    "condition": lambda save, game_state -> bool  # Fonction de vérification
}
```

### Paramètres détaillés :
- **nom** : Le titre affiché dans l'interface des quêtes
- **description** : Texte court expliquant l'objectif
- **section** : Doit être "quotidiennes", "missions", ou "evenements"
- **type_evenement** : 
  - `None` pour les quêtes non-événement
  - `"histoire"` pour les quêtes de l'histoire
  - `"guerre"` pour les quêtes de combat
  - `"infini"` pour les quêtes du mode infini
- **xp**, **pieces**, **gemmes** : Récompenses automatiques à la complétio
- **condition** : Fonction lambda qui retourne `True` quand la quête est complétée

## Exemples de conditions

### Quête simple basée sur le niveau
```python
"condition": lambda save, game_state: save.get("level", 1) >= 5
```

### Quête basée sur les combats remportés
```python
"condition": lambda save, game_state: save.get("battles_won", 0) >= 3
```

### Quête basée sur les ennemis tués
```python
"condition": lambda save, game_state: save.get("enemies_killed", 0) >= 50
```

### Quête combinée
```python
"condition": lambda save, game_state: (
    save.get("level", 1) >= 10 and 
    save.get("enemies_killed", 0) >= 100
)
```

## Variables disponibles dans `save`

Voici les variables de sauvegarde que vous pouvez vérifier :
- `save["level"]` - Niveau actuel du joueur
- `save["xp"]` - Points d'expérience actuels
- `save["coins"]` - Pièces d'or actuelles
- `save["gems"]` - Gemmes actuelles
- `save["battles_won"]` - Nombre de combats remportés
- `save["towers_placed"]` - Nombre de tours placées au total
- `save["enemies_killed"]` - Nombre d'ennemis tués au total
- `save["max_wave_reached"]` - Vague maximale atteinte
- `save["skill_points"]` - Points de compétence disponibles
- `save["inventory_equipment"]` - Liste des équipements

## Sections disponibles

### Quotidiennes (quotidiennes)
Quêtes qui se font une fois par jour. Exemples :
- Combattre 1 niveau
- Monter de 1 niveau
- Gagner 3 combats

### Missions (missions)
Quêtes de longue durée avec objectifs permanents. Exemples :
- Atteindre le niveau 10
- Tuer 50 ennemis
- Placer 10 tours

### Événements (evenements)
Quêtes d'événements spécifiques, organisées par type :
- **histoire** : Progression de l'histoire principale
- **guerre** : Combats intenses et objectives de combat
- **infini** : Mode infini avec objectifs de vagues

## Types de raretés des coffres

### Coffres à pièces
- **Bois** (30 pièces) : 70% Commun, 20% Rare, 8% Épique, 1% Légendaire, 1% Mythique
- **Argent** (80 pièces) : 45% Commun, 35% Rare, 15% Épique, 4% Légendaire, 1% Mythique
- **Or** (200 pièces) : 20% Commun, 25% Rare, 30% Épique, 20% Légendaire, 5% Mythique

### Coffres à gemmes (Beaucoup plus rares!)
- **Gemme Commun** (5 gemmes) : 5% Commun, 15% Rare, 30% Épique, 35% Légendaire, 15% Mythique
- **Gemme Épique** (15 gemmes) : 2% Commun, 8% Rare, 30% Épique, 40% Légendaire, 20% Mythique
- **Gemme Légendaire** (50 gemmes) : 0% Commun, 3% Rare, 15% Épique, 32% Légendaire, **50% Mythique**!

## Intégration dans le jeu

Pour que les quêtes se complètent, le jeu doit mettre à jour les statistiques. Exemple :

```python
# Dans game.py ou entities.py, quand le joueur gagne
save["battles_won"] = save.get("battles_won", 0) + 1
save["level"] = save.get("level", 0) + 1
save["enemies_killed"] = save.get("enemies_killed", 0) + 1

sd.save(save)  # Sauvegarder les données
```

## Exemple complet de quête personnalisée

```python
"mission_elite_waves": {
    "nom": "Guerrier de l'Infini",
    "description": "Atteignez la vague 50",
    "section": "evenements",
    "type_evenement": "infini",
    "xp": 200,
    "pieces": 1000,
    "gemmes": 5,
    "condition": lambda save, game_state: save.get("max_wave_reached", 0) >= 50
}
```

## Réclamation des récompenses

Quand un joueur réclame la récompense d'une quête complétée, les éléments suivants se produisent automatiquement :
1. Le XP est ajouté au joueur
2. Les pièces sont ajoutées à l'inventaire
3. Les gemmes sont ajoutées
4. La quête est marquée comme complétée et non réclaimable à nouveau

## Système de notification (À venir)

Un système de popup doit être implémenté pour notifier le joueur quand une quête est complétée, même en dehors du menu des quêtes. Le popup affichera :
- Nom de la quête
- "COMPLÉTÉE !"
- La récompense gagnée

Un clic sur le popup devrait naviguer vers le menu des quêtes à la section appropriée.

---

**Note** : Le système est entièrement flexible et peut être étendu pour supporter des conditions plus complexes, des récompenses personnalisées, ou même des quêtes en chaîne (quêtes qui débloquent d'autres quêtes).
