"""Markdown body templates, one per content type.

Templates only contain the body: the YAML front matter is generated from the
metadata, so a template never has to care about dates or tags.  ``{title}`` is
the only placeholder.

The section titles are in French because the portfolio itself is written in
French; the code around them stays in English.
"""

from __future__ import annotations

PROJECT_TEMPLATE = """# {title}

## Contexte

## Objectifs

## Fonctionnalités

## Technologies utilisées

## Résultats

## Ce que j'ai appris

## Améliorations possibles
"""

LAB_TEMPLATE = """# {title}

## Objectif du lab

## Matériel / environnement

## Étapes réalisées

## Résultats obtenus

## Problèmes rencontrés

## Ce que j'ai appris
"""

PUBLICATION_TEMPLATE = """# {title}

## Résumé

## Objectif

## Méthodologie

## Compétences mobilisées

## Sources et références
"""

READING_TEMPLATE = """# {title}

## Référence

## Résumé

## Idées principales

## Concepts à retenir

## Notes personnelles
"""

#: Body template for each content type.
TEMPLATES: dict[str, str] = {
    "project": PROJECT_TEMPLATE,
    "lab": LAB_TEMPLATE,
    "publication": PUBLICATION_TEMPLATE,
    "reading": READING_TEMPLATE,
}


def body_for(content_type: str, title: str) -> str:
    """Render the body template of ``content_type`` for ``title``.

    ``str.format`` is avoided on purpose: a title containing braces would
    otherwise crash the program.
    """
    template = TEMPLATES.get(content_type, PROJECT_TEMPLATE)
    return template.replace("{title}", title)
