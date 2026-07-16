from dotenv import load_dotenv

from rca.knowledge.retrieval import build_index

load_dotenv()


def main() -> None:
    counts = build_index()
    print(f"Knowledge index built: {counts['runbooks']} runbooks, {counts['past_incidents']} past incidents.")


if __name__ == "__main__":
    main()
