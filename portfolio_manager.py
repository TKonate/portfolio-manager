import argparse


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


if __name__ == "__main__":
    main()