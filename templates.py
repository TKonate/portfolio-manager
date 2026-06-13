#============================================
# TEMPLATES MARKDOWN
#============================================

# Ce fichier contient les modèles de fiches Markdown.
#
# Chaque template correspond à un type de contenu :
# - project
# - lab
# - publication
# - reading
#
# Dans chaque template, {title} sera remplacé automatiquement
# par le titre saisi par l'utilisateur.


#============================================
# TEMPLATE POUR UN PROJET
#============================================

PROJECT_TEMPLATE = """
# {title}

## Contexte

## Objectifs

## Fonctionnalités prévues

## Technologies utilisées

## Ce que j’ai appris

## Améliorations possibles
"""


#============================================
# TEMPLATE POUR UN LAB
#============================================

LAB_TEMPLATE = """
# {title}

## Objectif du lab

## Matériel / environnement

## Étapes réalisées

## Résultats obtenus

## Problèmes rencontrés

## Ce que j’ai appris
"""


#============================================
# TEMPLATE POUR UNE PUBLICATION
#============================================

PUBLICATION_TEMPLATE = """
# {title}

## Résumé

## Objectif

## Méthodologie

## Compétences mobilisées

## Sources et références
"""


#============================================
# TEMPLATE POUR UNE NOTE DE LECTURE
#============================================

READING_TEMPLATE = """
# {title}

## Référence

## Résumé

## Idées principales

## Concepts à retenir

## Notes personnelles
"""


#============================================
# ASSOCIATION ENTRE TYPES ET TEMPLATES
#============================================

# Ce dictionnaire permet de retrouver rapidement le bon template
# à partir du type demandé dans la ligne de commande.
#
# Exemple :
# TEMPLATES["publication"] renvoie PUBLICATION_TEMPLATE.
TEMPLATES = {
    "project": PROJECT_TEMPLATE,
    "lab": LAB_TEMPLATE,
    "publication": PUBLICATION_TEMPLATE,
    "reading": READING_TEMPLATE,
}