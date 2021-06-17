from .schema import Base
import sqlalchemy.orm


def get_session(db_path: str) -> sqlalchemy.orm.Session:
    engine = sqlalchemy.create_engine(f"sqlite:///{db_path}")
    Session = sqlalchemy.orm.sessionmaker(engine)
    db_session = Session()
    Base.metadata.create_all(engine)
    return db_session
