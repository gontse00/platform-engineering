from app.db import Base, engine
from models.graph import GraphNodeDB, GraphEdgeDB  # noqa: F401
from models.search import SearchDocumentDB  # noqa: F401


def main():
    Base.metadata.create_all(bind=engine)
    print("Graph tables created successfully.")


if __name__ == "__main__":
    main()