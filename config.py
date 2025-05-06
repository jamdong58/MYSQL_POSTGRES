
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

# Paramètres MySQL
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'malick1958'
MYSQL_HOST = 'localhost'

# Bases à connecter
bases_mysql = ['Babs_BD', 'Dione_BD','Ras_BD', 'idia_BD']

# Connexions MySQL (un dictionnaire)
db_mysql_connections = {}

for base in bases_mysql:
    engine = create_engine(f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{base}", echo=False)
    Session = scoped_session(sessionmaker(bind=engine))
    db_mysql_connections[base] = Session()

# Paramètres PostgreSQL
POSTGRES_USER = 'postgres'
POSTGRES_PASSWORD = 'elmalick2025'
POSTGRES_HOST = 'localhost'
POSTGRES_DB = 'sasuke'

# Connexion PostgreSQL
postgres_engine = create_engine(f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DB}", echo=False)
db_postgres_session = scoped_session(sessionmaker(bind=postgres_engine))
