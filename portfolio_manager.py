import argparse
import re
import unicodedata
from pathlib import Path

from templates import TEMPLATES


CONTENT_FOLDERS = {
    "project": "projects",
    "lab": "labs",
    "publication": "publications",
    "reading": "reading",
}


VALID_DOMAINS = {
    "technology": ["computer-science", "electronics"],
    "security": ["cybersecurity", "osint"],
    "society": ["political-science", "sociology"],
    "interdisciplinary": ["general"],
}


def build_file_path(metadata, content_type, filename):
    """Build the destination path for the Markdown file."""

    portfolio_root = Path("portfolio")

    folder_name = CONTENT_FOLDERS[content_type]

    file_path = (
        portfolio_root
        / "content"
        / metadata["domain"]
        / metadata["subdomain"]
        / folder_name
        / filename
    )

    return file_path


def create_markdown_file(file_path, markdown_content):
    """Create a Markdown file, without overwriting an existing file."""

    if file_path.exists():
        print(f"Erreur : le fichier existe déjà : {file_path}")
        return

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(markdown_content, encoding="utf-8")

    print(f"Fichier créé : {file_path}")


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


def parse_tags(tags_text):
    """Convert a comma-separated tags string into a clean list of tags."""

    tags = tags_text.split(",")

    clean_tags = []
    for tag in tags:
        clean_tag = tag.strip()
        if clean_tag:
            clean_tags.append(clean_tag)

    return clean_tags


def generate_front_matter(metadata, content_type):
    """Generate a YAML front matter block from metadata."""

    tags = parse_tags(metadata["tags"])

    front_matter = "---\n"
    front_matter += f'title: "{metadata["title"]}"\n'
    front_matter += f'type: "{content_type}"\n'
    front_matter += f'date: {metadata["date"]}\n'
    front_matter += "tags:\n"

    for tag in tags:
        front_matter += f"  - {tag}\n"

    front_matter += 'status: "draft"\n'
    front_matter += "---\n"

    return front_matter


def generate_markdown_content(metadata, content_type):
    """Generate the full Markdown content using front matter and a template."""

    front_matter = generate_front_matter(metadata, content_type)

    template = TEMPLATES[content_type]
    body = template.format(title=metadata["title"])

    return front_matter + body


def ask_metadata():
    """Ask the user for the metadata needed to create a portfolio entry."""

    title = input("Title: ").strip()
    domain = input("Domain: ").strip().lower()
    subdomain = input("Subdomain: ").strip().lower()
    tags = input("Tags, separated by commas: ").strip()
    date = input("Date: ").strip()

    return {
        "title": title,
        "domain": domain,
        "subdomain": subdomain,
        "tags": tags,
        "date": date,
    }


def validate_metadata(metadata):
    """Validate user metadata before creating a file."""

    if not metadata["title"]:
        print("Erreur : le titre ne peut pas être vide.")
        return False

    if metadata["domain"] not in VALID_DOMAINS:
        print(f"Erreur : domaine inconnu : {metadata['domain']}")
        print("Domaines autorisés :")
        for domain in VALID_DOMAINS:
            print(f"- {domain}")
        return False

    valid_subdomains = VALID_DOMAINS[metadata["domain"]]

    if metadata["subdomain"] not in valid_subdomains:
        print(f"Erreur : sous-domaine invalide pour {metadata['domain']} : {metadata['subdomain']}")
        print("Sous-domaines autorisés :")
        for subdomain in valid_subdomains:
            print(f"- {subdomain}")
        return False

    return True


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
        choices=CONTENT_FOLDERS.keys(),
        help="Type de contenu à créer."
    )

    args = parser.parse_args()

    if args.command != "new":
        print(f"Erreur : commande inconnue : {args.command}")
        print("Commande disponible : new")
        return

    print(f"Commande demandée : {args.command}")
    print(f"Type de contenu : {args.content_type}")
    print()

    metadata = ask_metadata()

    if not validate_metadata(metadata):
        return

    print()
    print("Métadonnées récupérées :")
    print(f"Title: {metadata['title']}")
    print(f"Domain: {metadata['domain']}")
    print(f"Subdomain: {metadata['subdomain']}")
    print(f"Tags: {metadata['tags']}")
    print(f"Date: {metadata['date']}")


    filename = slugify(metadata["title"]) + ".md"
    print(f"Nom de fichier généré : {filename}")


    markdown_content = generate_markdown_content(metadata, args.content_type)

    file_path = build_file_path(metadata, args.content_type, filename)

    print()
    print(f"Chemin du fichier : {file_path}")

    create_markdown_file(file_path, markdown_content)


if __name__ == "__main__":
    main()