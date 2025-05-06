


from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date
from sqlalchemy.orm import relationship, declarative_base
from config import postgres_engine

Base = declarative_base()

# --- Table Client ---
class Client(Base):
    __tablename__ = 'CLIENT'  
    id_client = Column(Integer, primary_key=True, autoincrement=True)
    nom = Column(String(100))
    prenom = Column(String(100))
    ville = Column(String(100))
    email = Column(String(150))
    commandes = relationship('Commande', back_populates='client')
    avis = relationship('Avis', back_populates='client')

# --- Table Produit ---
class Produit(Base):
    __tablename__ = 'PRODUIT'  
    id_produit = Column(Integer, primary_key=True, autoincrement=True)
    nom_produit = Column(String(100))
    categorie = Column(String(100))
    prix = Column(Float)
    stock = Column(Integer)
    ligne_commandes = relationship('LigneCommande', back_populates='produit')
    avis = relationship('Avis', back_populates='produit')

# --- Table Vendeur ---
class Vendeur(Base):
    __tablename__ = 'VENDEUR'  
    id_vendeur = Column(Integer, primary_key=True, autoincrement=True)
    nom = Column(String(100))
    agence = Column(String(100))
    commandes = relationship('Commande', back_populates='vendeur')

# --- Table Commande ---
class Commande(Base):
    __tablename__ = 'COMMANDE'  
    id_commande = Column(Integer, primary_key=True, autoincrement=True)
    id_client = Column(Integer, ForeignKey('CLIENT.id_client'))  
    id_vendeur = Column(Integer, ForeignKey('VENDEUR.id_vendeur'))  
    date_commande = Column(Date)
    statut = Column(String(50))
    client = relationship('Client', back_populates='commandes')
    vendeur = relationship('Vendeur', back_populates='commandes')
    ligne_commandes = relationship('LigneCommande', back_populates='commande')

# --- Table LigneCommande ---
class LigneCommande(Base):
    __tablename__ = 'LIGNE_COMMANDE'
    id_commande = Column(Integer, ForeignKey('COMMANDE.id_commande'), primary_key=True)
    id_produit = Column(Integer, ForeignKey('PRODUIT.id_produit'), primary_key=True)
    quantite = Column(Integer)
    remise = Column(Float)
    commande = relationship('Commande', back_populates='ligne_commandes')
    produit = relationship('Produit', back_populates='ligne_commandes')

# --- Table Avis ---
class Avis(Base):
    __tablename__ = 'AVIS'
    id_avis = Column(Integer, primary_key=True, autoincrement=True)
    id_client = Column(Integer, ForeignKey('CLIENT.id_client'))  
    id_produit = Column(Integer, ForeignKey('PRODUIT.id_produit'))  
    note = Column(Float)
    commentaire = Column(String(255))
    client = relationship('Client', back_populates='avis')
    produit = relationship('Produit', back_populates='avis')

# --- Création des tables dans PostgreSQL si elles n'existent pas ---
Base.metadata.create_all(bind=postgres_engine)



