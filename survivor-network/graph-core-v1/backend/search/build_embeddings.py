from app.db import SessionLocal
from services.search_service import SearchService


def main():
    db = SessionLocal()
    try:
        count = SearchService.build_embeddings_for_all_documents(db)
        print(f"Embeddings built for {count} documents.")
    finally:
        db.close()


if __name__ == "__main__":
    main()