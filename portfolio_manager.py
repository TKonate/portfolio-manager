#============================================
# PORTFOLIO MANAGER
# Outil CLI pour créer des fichiers Markdown
#============================================

# Ce programme permet de créer automatiquement une fiche Markdown
# dans une arborescence de portfolio.
#
# Exemple d'utilisation :
# python portfolio_manager.py new publication


#============================================
# IMPORTS
#============================================

# argparse permet de lire les arguments donnés dans le terminal.
# Exemple :
# python portfolio_manager.py new publication
import argparse

# json permet de lire les fichiers json
import json

# re permet d'utiliser des expressions régulières.
# Ici, on s'en sert pour nettoyer le titre et créer un nom de fichier propre.
import re

# unicodedata permet de supprimer les accents dans les noms de fichiers.
# Exemple : "souverainetés" devient "souverainetes".
import unicodedata

# pathlib permet de manipuler les chemins de fichiers proprement.
# C'est plus lisible et plus compatible que de construire les chemins à la main.
from pathlib import Path

# On importe les templates Markdown définis dans le fichier templates.py.
from templates import TEMPLATES


#============================================
# CONFIGURATION DU PORTFOLIO
#============================================

# Dossiers associés à chaque type de contenu.
#
# L'utilisateur écrit le type au singulier :
# publication
#
# Mais le dossier correspondant est au pluriel :
# publications/
CONTENT_FOLDERS = {
    "project": "projects",
    "lab": "labs",
    "publication": "publications",
    "reading": "reading",
}


# Domaines et sous-domaines autorisés.
#
# Cela évite de créer des fichiers dans des dossiers mal nommés.
# Exemple :
# society accepte political-science et sociology,
# mais pas electronics.
VALID_DOMAINS = {
    "technology": ["computer-science", "electronics"],
    "security": ["cybersecurity", "osint"],
    "society": ["political-science", "sociology"],
    "interdisciplinary": ["general"],
}


#============================================
# GENERATION DU NOM DE FICHIER
#============================================

def slugify(title):
    """
    Transforme un titre en nom de fichier propre.

    Exemple :
    "Populations civiles et souverainetés fragmentées"

    devient :
    "populations-civiles-et-souverainetes-fragmentees"

    Paramètre :
    - title : titre saisi par l'utilisateur.

    Retour :
    - slug : version nettoyée du titre, utilisable comme nom de fichier.
    """

    # 1. Normalisation du texte :
    # on sépare les lettres de leurs accents.
    normalized_title = unicodedata.normalize("NFKD", title)

    # 2. Conversion en ASCII :
    # les accents sont supprimés.
    ascii_title = normalized_title.encode("ascii", "ignore").decode("ascii")

    # 3. Passage en minuscules.
    slug = ascii_title.lower()

    # 4. Remplacement des caractères non autorisés par des tirets.
    #
    # [^a-z0-9]+ signifie :
    # tout ce qui n'est pas une lettre minuscule ou un chiffre.
    slug = re.sub(r"[^a-z0-9]+", "-", slug)

    # 5. Suppression des tirets au début et à la fin.
    slug = slug.strip("-")

    return slug


#============================================
# TRAITEMENT DES TAGS
#============================================

def parse_tags(tags_text):
    """
    Transforme une chaîne de tags séparés par des virgules en liste.

    Exemple :
    "python, cli, markdown"

    devient :
    ["python", "cli", "markdown"]

    Paramètre :
    - tags_text : texte saisi par l'utilisateur.

    Retour :
    - clean_tags : liste de tags nettoyés.
    """

    # On découpe le texte à chaque virgule.
    tags = tags_text.split(",")

    # Cette liste contiendra les tags nettoyés.
    clean_tags = []

    # On parcourt tous les tags saisis.
    for tag in tags:

        # On enlève les espaces inutiles au début et à la fin.
        clean_tag = tag.strip()

        # Si le tag n'est pas vide, on l'ajoute à la liste.
        if clean_tag:
            clean_tags.append(clean_tag)

    return clean_tags


#============================================
# QUESTIONS POSEES A L'UTILISATEUR
#============================================

def ask_metadata():
    """
    Demande à l'utilisateur les informations nécessaires
    pour créer une fiche Markdown.

    Retour :
    - metadata : dictionnaire contenant les informations saisies.
    """

    # Titre affiché dans le fichier Markdown.
    title = input("Title: ").strip()

    # Domaine principal du portfolio.
    # On met en minuscules pour éviter les erreurs liées aux majuscules.
    domain = input("Domain: ").strip().lower()

    # Sous-domaine du portfolio.
    subdomain = input("Subdomain: ").strip().lower()

    # Tags séparés par des virgules.
    tags = input("Tags, separated by commas: ").strip()

    # Date associée au contenu.
    date = input("Date: ").strip()

    # On regroupe toutes les informations dans un dictionnaire.
    metadata = {
        "title": title,
        "domain": domain,
        "subdomain": subdomain,
        "tags": tags,
        "date": date,
    }

    return metadata


#============================================
# VALIDATION DES DONNEES
#============================================

def validate_metadata(metadata):
    """
    Vérifie que les informations saisies sont valides.

    Paramètre :
    - metadata : dictionnaire contenant les réponses de l'utilisateur.

    Retour :
    - True si les données sont valides ;
    - False sinon.
    """

    #-----------------------------
    # 1. Vérification du titre
    #-----------------------------

    if not metadata["title"]:
        print("Erreur : le titre ne peut pas être vide.")
        return False

    #-----------------------------
    # 2. Vérification du domaine
    #-----------------------------

    if metadata["domain"] not in VALID_DOMAINS:
        print(f"Erreur : domaine inconnu : {metadata['domain']}")
        print("Domaines autorisés :")

        for domain in VALID_DOMAINS:
            print(f"- {domain}")

        return False

    #-----------------------------
    # 3. Vérification du sous-domaine
    #-----------------------------

    # On récupère la liste des sous-domaines valides
    # pour le domaine choisi.
    valid_subdomains = VALID_DOMAINS[metadata["domain"]]

    if metadata["subdomain"] not in valid_subdomains:
        print(
            f"Erreur : sous-domaine invalide pour {metadata['domain']} : "
            f"{metadata['subdomain']}"
        )

        print("Sous-domaines autorisés :")

        for subdomain in valid_subdomains:
            print(f"- {subdomain}")

        return False

    return True


#============================================
# GENERATION DU FRONT MATTER YAML
#============================================

def generate_front_matter(metadata, content_type):
    """
    Génère le front matter YAML du fichier Markdown.

    Paramètres :
    - metadata : informations saisies par l'utilisateur ;
    - content_type : type de contenu à créer.

    Retour :
    - front_matter : texte YAML placé au début du fichier Markdown.
    """

    # On transforme les tags saisis en liste propre.
    tags = parse_tags(metadata["tags"])

    # Début du front matter.
    front_matter = "---\n"

    # Titre du contenu.
    front_matter += f'title: "{metadata["title"]}"\n'

    # Type du contenu : project, lab, publication ou reading.
    front_matter += f'type: "{content_type}"\n'

    # Date du contenu.
    front_matter += f'date: {metadata["date"]}\n'

    # Liste des tags.
    front_matter += "tags:\n"

    for tag in tags:
        front_matter += f"  - {tag}\n"

    # Statut par défaut.
    front_matter += 'status: "draft"\n'

    # Fin du front matter.
    front_matter += "---\n"

    return front_matter


#============================================
# GENERATION DU CONTENU MARKDOWN
#============================================

def generate_markdown_content(metadata, content_type):
    """
    Génère le contenu complet du fichier Markdown.

    Le fichier contient :
    - un front matter YAML ;
    - un corps Markdown basé sur un template.

    Paramètres :
    - metadata : informations saisies par l'utilisateur ;
    - content_type : type de contenu à créer.

    Retour :
    - markdown_content : contenu complet du fichier.
    """

    # 1. Génération du front matter.
    front_matter = generate_front_matter(metadata, content_type)

    # 2. Récupération du template correspondant au type de contenu.
    template = TEMPLATES[content_type]

    # 3. Insertion du titre dans le template.
    body = template.format(title=metadata["title"])

    # 4. Assemblage du front matter et du corps Markdown.
    markdown_content = front_matter + body

    return markdown_content


#============================================
# CONSTRUCTION DU CHEMIN DU FICHIER
#============================================

def build_file_path(portfolio_root, metadata, content_type, filename):
    """
    Construit le chemin du fichier Markdown à créer.

    Paramètres :
    - portfolio_root : chemin vers le dossier racine du portfolio ;
    - metadata : informations saisies par l'utilisateur ;
    - content_type : type de contenu ;
    - filename : nom du fichier Markdown.

    Retour :
    - file_path : chemin complet du fichier.
    """

    # On récupère le nom du dossier associé au type de contenu.
    folder_name = CONTENT_FOLDERS[content_type]

    # Construction du chemin final.
    file_path = (
        portfolio_root
        / "content"
        / metadata["domain"]
        / metadata["subdomain"]
        / folder_name
        / filename
    )

    return file_path


#============================================
# CREATION DU FICHIER MARKDOWN
#============================================

def create_markdown_file(file_path, markdown_content):
    """
    Crée le fichier Markdown sur le disque.

    Le programme refuse d'écraser un fichier déjà existant.

    Paramètres :
    - file_path : chemin du fichier à créer ;
    - markdown_content : contenu à écrire dans le fichier.

    Retour :
    - True si le fichier a été créé ;
    - False sinon.
    """

    #-----------------------------
    # 1. Protection anti-écrasement
    #-----------------------------

    if file_path.exists():
        print(f"Erreur : le fichier existe déjà : {file_path}")
        return False

    #-----------------------------
    # 2. Création des dossiers parents
    #-----------------------------

    # parents=True permet de créer toute l'arborescence manquante.
    # exist_ok=True évite une erreur si le dossier existe déjà.
    file_path.parent.mkdir(parents=True, exist_ok=True)

    #-----------------------------
    # 3. Ecriture du fichier
    #-----------------------------

    # encoding="utf-8" permet de gérer correctement les accents.
    file_path.write_text(markdown_content, encoding="utf-8")

    print(f"Fichier créé : {file_path}")

    return True


#============================================
# LECTURE DE LA CONFIGURATION
#============================================

def load_config():
    """
    Charge la configuration du projet depuis config.json.

    Retour :
    - config : dictionnaire contenant les paramètres du programme.
    """

    # Chemin du fichier de configuration.
    config_path = Path("config.json")

    # Si le fichier n'existe pas, on affiche une erreur claire.
    if not config_path.exists():
        print("Erreur : fichier config.json introuvable.")
        print("Crée un fichier config.json avec un champ portfolio_root.")
        return None

    # Si le fichier existe mais qu'il est vide, on affiche une erreur claire.
    if config_path.stat().st_size == 0:
        print("Erreur : config.json est vide.")
        print('Ajoute par exemple : { "portfolio_root": "../portfolio" }')
        return None

    # Lecture du fichier JSON.
    config_text = config_path.read_text(encoding="utf-8")

    try:
        # Conversion du texte JSON en dictionnaire Python.
        config = json.loads(config_text)

    except json.JSONDecodeError:
        print("Erreur : config.json n'est pas un JSON valide.")
        print("Exemple attendu :")
        print('{')
        print('  "portfolio_root": "../portfolio"')
        print('}')
        return None

    # Vérification de la présence du champ obligatoire.
    if "portfolio_root" not in config:
        print('Erreur : le champ "portfolio_root" est absent de config.json.')
        return None

    return config


#============================================
# VALIDATION DU CHEMIN DU PORTFOLIO
#============================================

def validate_portfolio_root(portfolio_root):
    """
    Vérifie que le chemin du portfolio semble valide.

    Un portfolio valide doit contenir un dossier content/.

    Paramètre :
    - portfolio_root : chemin vers le dossier racine du portfolio.

    Retour :
    - True si le chemin semble valide ;
    - False sinon.
    """

    # Vérification de l'existence du dossier racine.
    if not portfolio_root.exists():
        print(f"Erreur : le dossier portfolio n'existe pas : {portfolio_root}")
        return False

    # Vérification que le chemin pointe bien vers un dossier.
    if not portfolio_root.is_dir():
        print(f"Erreur : ce chemin n'est pas un dossier : {portfolio_root}")
        return False

    # Vérification de la présence du dossier content/.
    content_root = portfolio_root / "content"

    if not content_root.exists():
        print(f"Erreur : le dossier content/ est introuvable dans : {portfolio_root}")
        print("Vérifie la valeur de portfolio_root dans config.json.")
        return False

    return True

#============================================
# PROGRAMME PRINCIPAL
#============================================

def main():
    """
    Fonction principale du programme.

    Elle :
    1. lit les arguments de la ligne de commande ;
    2. vérifie la commande demandée ;
    3. pose les questions à l'utilisateur ;
    4. valide les réponses ;
    5. génère le fichier Markdown.
    """

    #-----------------------------
    # 1. Configuration du parser
    #-----------------------------

    parser = argparse.ArgumentParser(
        description="Portfolio Manager - outil de gestion de fichiers Markdown pour portfolio."
    )

    # Premier argument : commande à exécuter.
    #
    # Exemple :
    # python portfolio_manager.py new publication
    #
    # Ici, "new" est la commande.
    parser.add_argument(
        "command",
        help="Commande à exécuter. Exemple : new"
    )

    # Deuxième argument : type de contenu.
    #
    # Exemple :
    # python portfolio_manager.py new publication
    #
    # Ici, "publication" est le type de contenu.
    parser.add_argument(
        "content_type",
        choices=list(CONTENT_FOLDERS.keys()),
        help="Type de contenu à créer."
    )

    # Lecture des arguments du terminal.
    args = parser.parse_args()


    config = load_config()

    if config is None:
        return

    portfolio_root = Path(config["portfolio_root"])
    
    print(f"Portfolio configuré : {config['portfolio_root']}")

    if not validate_portfolio_root(portfolio_root):
        return

    #-----------------------------
    # 2. Vérification de la commande
    #-----------------------------

    if args.command != "new":
        print(f"Erreur : commande inconnue : {args.command}")
        print("Commande disponible : new")
        return

    #-----------------------------
    # 3. Affichage de confirmation
    #-----------------------------

    print(f"Commande demandée : {args.command}")
    print(f"Type de contenu : {args.content_type}")
    print()

    #-----------------------------
    # 4. Récupération des métadonnées
    #-----------------------------

    metadata = ask_metadata()

    #-----------------------------
    # 5. Validation des métadonnées
    #-----------------------------

    if not validate_metadata(metadata):
        return

    #-----------------------------
    # 6. Génération du nom de fichier
    #-----------------------------

    filename = slugify(metadata["title"]) + ".md"

    print()
    print(f"Nom de fichier généré : {filename}")

    #-----------------------------
    # 7. Génération du contenu Markdown
    #-----------------------------

    markdown_content = generate_markdown_content(
        metadata,
        args.content_type
    )

    #-----------------------------
    # 8. Construction du chemin final
    #-----------------------------

    file_path = build_file_path(
        portfolio_root,
        metadata,
        args.content_type,
        filename
    )

    print(f"Chemin du fichier : {file_path}")

    #-----------------------------
    # 9. Création du fichier
    #-----------------------------

    create_markdown_file(file_path, markdown_content)


#============================================
# POINT D'ENTREE DU PROGRAMME
#============================================

# Cette condition signifie :
# lance main() seulement si ce fichier est exécuté directement.
#
# Exemple :
# python portfolio_manager.py new publication
if __name__ == "__main__":
    main()