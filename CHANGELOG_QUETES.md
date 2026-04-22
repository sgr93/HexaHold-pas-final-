# CHANGELOG - Système de Quêtes HexaHold

## ✅ Modifications implémentées

### 1. **Nouveau fichier : quetes.py**
- Système de gestion des quêtes complètement flexible
- Support pour 3 sections : Quotidiennes, Missions, Événements
- 3 types d'événements : Histoire, Guerre, Infini
- 18 quêtes pré-configurées pour commencer
- Système de conditions lambda pour vérifier l'accomplissement
- Fonctions utilitaires :
  - `get_quests_by_section()` - Récupère les quêtes d'une section
  - `get_event_quests_by_type()` - Récupère les quêtes d'un type d'événement
  - `check_quest_completion()` - Vérifie si une quête est complétée
  - `claim_quest_reward()` - Réclame la récompense (automatique)
  - `get_available_quests()` - Quêtes disponibles à réclamer

### 2. **Modifications config.py**
- ✅ 3 nouveaux types de coffres à gemmes
  - `gem_common` (5 gemmes) - Raretés plus hautes
  - `gem_epic` (15 gemmes) - Beaucoup de Légendaires/Mythiques
  - `gem_legendary` (50 gemmes) - 50% Mythique !
- ✅ Nouvelle rareté : "Mythique" (5e rareté) - Couleur magenta
- ✅ Statistiques réduites pour les coffres normaux (pièces)
  - Bois : -10 Rare, -1 Épique
  - Argent : -10 Rare, -7 Épique
  - Or : -15 Rare, -5 Épique
- ✅ Nouvelles valeurs d'équipement pour la rareté Mythique

### 3. **Modifications save_data.py**
- ✅ Ajout du support des gemmes (`save["gems"]`)
- ✅ Nouveau système de sauvegarde pour les quêtes
  - `save["quests_completed"]` - Quêtes récompensées
  - `save["daily_quests_completed"]` - État des quêtes quotidiennes
  - `save["events_completed"]` - État des événements complétés
- ✅ Nouvelle structure de données par défaut (_DEFAULT)
  - Statistiques du joueur :
    - `level` (défaut : 1)
    - `xp` (défaut : 0)
    - `battles_won` (défaut : 0)
    - `towers_placed` (défaut : 0)
    - `enemies_killed` (défaut : 0)
    - `max_wave_reached` (défaut : 0)
- ✅ Modification de `open_chest()` pour supporter les coffres à gemmes
  - Détection automatique du type de coffre (pièces vs gemmes)
  - Déduction correcte des ressources
  - Support pour la nouvelle rareté Mythique

### 4. **Modifications menu_screen.py**
- ✅ Affichage des gemmes dans le header à côté des pièces
- ✅ Nouvelle icône "gem" vectorielle
- ✅ Nouvel onglet "Quêtes" (5e onglet)
- ✅ Interface gacha redessinée avec 2 rangées
  - Rangée 1 : Coffres à pièces (Bois, Argent, Or)
  - Rangée 2 : Coffres à gemmes (3 niveaux)
- ✅ Système de quêtes complet dans le nouvel onglet :
  - 3 sections avec onglets (Quotidiennes, Missions, Événements)
  - Pour Événements : Système de défilement (< >) entre Histoire/Guerre/Infini
  - Affichage détaillé de chaque quête :
    - Nom et description
    - Récompenses (XP, Pièces, Gemmes)
    - Statut (Complétée/Réclaimable/En cours)
  - Bouton "Réclamer" pour les quêtes complétées
  - Indication visuelle pour les récompenses

### 5. **Support pour RARITY_COLORS mis à jour**
- Mythique : (255, 0, 255) - Magenta vibrante

## 🎮 Fonctionnalités

### Système de Quêtes
1. **Sections de quêtes** :
   - Quotidiennes : Petites quêtes d'une fois par jour
   - Missions : Quêtes de progression longue
   - Événements : 3 types (Histoire, Guerre, Infini)

2. **Récompenses** :
   - XP (augmente le niveau)
   - Pièces (pour les coffres)
   - Gemmes (pour les coffres premium)

3. **Interface** :
   - Visualisation complète des quêtes disponibles
   - Affichage du statut de chaque quête
   - Navigation facile entre sections
   - Défilement des événements

4. **Automatisation** :
   - Les conditions se vérifient automatiquement
   - Les récompenses s'ajoutent à la réclamation
   - Système flexible pour ajouter des quêtes

### Système de Coffres Amélioré
1. **Coffres à pièces** :
   - Probabilités réduites pour les raretés hautes
   - Coûts : 30, 80, 200 pièces

2. **Coffres à gemmes** (NOUVEAU) :
   - Coffre Commun : 5 gemmes - Rare mais recommandé
   - Coffre Épique : 15 gemmes - Beaucoup de Légendaires
   - Coffre Légendaire : 50 gemmes - 50% Mythique!

3. **Nouvelle rareté Mythique** :
   - Obtenu principalement dans les coffres à gemmes
   - Statistiques très élevées
   - Couleur distinctive (magenta)

## 📊 Quêtes pré-configurées

### Quotidiennes (3)
- Combat du jour (1 niveau)
- Guerrier du jour (3 niveaux)
- Augmentation de puissance (monter de 1 niveau)

### Missions (7)
- Guerrier confirmé (niveau 5)
- Maître des combats (niveau 10) - 1 gemme
- Triple attaque (3 combats)
- Inarrêtable (5 combats) - 1 gemme
- Constructeur (placer 1 tour)
- Architecte militaire (placer 10 tours) - 1 gemme

### Événements

**Histoire (2)**
- Le commencement (niveau 1 Normal)
- Rencontre du boss (atteindre le boss niveau 2) - 1 gemme

**Guerre (3)**
- Premières victimes (50 ennemis)
- Carnage (200 ennemis) - 2 gemmes
- Généralissime (niveau 5 Très Difficile) - 2 gemmes

**Infini (3)**
- Commençant l'infini (vague 10)
- Guerrier sans fin (vague 30) - 3 gemmes
- Légende vivante (vague 50) - 5 gemmes

## ⚙️ Configuration requise

- Python 3.7+
- pygame
- json (standard library)

## 🔧 Comment tester

1. Lancer le jeu : `python main.py`
2. Aller au menu principal
3. Cliquer sur l'onglet "Quêtes"
4. Voir les quêtes disponibles
5. Les quêtes se complètent automatiquement quand les conditions sont atteintes

## 📝 Comment ajouter des quêtes

Voir le fichier `QUETES_README.md` pour une documentation complète sur :
- La structure des quêtes
- Comment créer des conditions personnalisées
- Les variables disponibles
- Les exemples de quêtes

## 🚀 Améliorations futures

- [ ] Système de notification popup pour les quêtes complétées
- [ ] Quêtes en chaîne (déblocage de quêtes)
- [ ] Réinitialisation quotidienne des quêtes quotidiennes
- [ ] Progression visuelle (barres de progression)
- [ ] Quêtes aléatoires
- [ ] Récompenses personnalisées (pas juste XP/pièces/gemmes)

---

**Statut** : ✅ Implémentation complète du système de quêtes et des coffres à gemmes
**Date** : 2026-04-22
**Version** : 1.0.0
