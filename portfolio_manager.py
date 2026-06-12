import argparse
import re
import unicodedata


def slugify(title):
    """Convert a title into a safe filename slug."""

    # Convert accented characters to non-accented characters
    normalized_title = unicodedata.normalize("NFKD", title)
    ascii_title = normalized_title.encode("ascii", "ignore").decode("ascii")

    # Convert to lowercase
    slug = ascii_title.lower()

    # Replace everything that is not a letter or number with a dash
    slug = re.sub(r"[^a-z0-9]+", "-", slug)

    # Remove leading and trailing dashes
    slug = slug.strip("-")

    return slug

def ask_metadata():
    """Ask the user for the metadata needed to create a portfolio entry."""

    title = input("Title: ")
    domain = input("Domain: ")
    subdomain = input("Subdomain: ")
    tags = input("Tags, separated by commas: ")
    date = input("Date: ")

    return {
        "title": title,
        "domain": domain,
        "subdomain": subdomain,
        "tags": tags,
        "date": date,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Portfolio Manager - outil de gestion de fichiers Markdown pour portfolio."
    )

    parser.add_argument(
        "command",
        help="Commande à exécuter. Exemple : new"
    )

    parser.add_argument(
        "content_type",
        help="Type de contenu à créer. Exemple : project, lab, publication, reading"
    )

    args = parser.parse_args()

    print(f"Commande demandée : {args.command}")
    print(f"Type de contenu : {args.content_type}")
    print()

    metadata = ask_metadata()

    print()
    print("Métadonnées récupérées :")
    print(f"Title: {metadata['title']}")
    print(f"Domain: {metadata['domain']}")
    print(f"Subdomain: {metadata['subdomain']}")
    print(f"Tags: {metadata['tags']}")
    print(f"Date: {metadata['date']}")

    filename = slugify(metadata["title"]) + ".md"
    print(f"Nom de fichier généré : {filename}")


if __name__ == "__main__":
    main()