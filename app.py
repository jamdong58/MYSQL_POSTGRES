from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import text, inspect
from config import db_mysql_connections, db_postgres_session, bases_mysql
from models import Base, Client, Produit, Vendeur, Commande, LigneCommande, Avis
import json
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, MetaData, Table, ForeignKey

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Création d'une table de suivi pour les transferts dans PostgreSQL
class TransferLog(Base):
    __tablename__ = 'transfer_log'
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_db = Column(String(100))
    source_table = Column(String(100))
    source_id = Column(Integer)
    target_id = Column(Integer)

# Créer la table de suivi si elle n'existe pas
metadata = MetaData()
try:
    Base.metadata.create_all(bind=db_postgres_session.get_bind())
except:
    pass

# Dictionnaire pour stocker la structure des tables MySQL
mysql_tables = {
    'CLIENT': {
        'columns': ['id_client', 'nom', 'prenom', 'ville', 'email'],
        'class': Client
    },
    'PRODUIT': {
        'columns': ['id_produit', 'nom_produit', 'categorie', 'prix', 'stock'],
        'class': Produit
    },
    'VENDEUR': {
        'columns': ['id_vendeur', 'nom', 'agence'],
        'class': Vendeur
    },
    'COMMANDE': {
        'columns': ['id_commande', 'id_client', 'id_vendeur', 'date_commande', 'statut'],
        'class': Commande
    },
    'LIGNE_COMMANDE': {
        'columns': ['id_commande', 'id_produit', 'quantite', 'remise'],
        'class': LigneCommande
    },
    'AVIS': {
        'columns': ['id_avis', 'id_client', 'id_produit', 'note', 'commentaire'],
        'class': Avis
    }
}

# Ordre des tables pour respecter les dépendances
table_order = ['CLIENT', 'PRODUIT', 'VENDEUR', 'COMMANDE', 'LIGNE_COMMANDE', 'AVIS']

@app.route('/')
def index():
    return render_template('index.html', bases=bases_mysql)

@app.route('/tables/<db_name>')
def show_tables(db_name):
    if db_name not in bases_mysql:
        flash('Base de données non trouvée')
        return redirect(url_for('index'))
    
    return render_template('tables.html', db_name=db_name, tables=table_order)

@app.route('/data/<db_name>/<table_name>')
def show_data(db_name, table_name):
    if db_name not in bases_mysql:
        flash('Base de données non trouvée')
        return redirect(url_for('index'))
    
    if table_name not in mysql_tables:
        flash('Table non trouvée')
        return redirect(url_for('show_tables', db_name=db_name))
    
    try:
        # Récupérer les données de la table MySQL
        mysql_session = db_mysql_connections[db_name]
        query = text(f"SELECT * FROM {table_name}")
        result = mysql_session.execute(query)
        
        # Convertir les résultats en liste de dictionnaires
        data = []
        for row in result:
            item = {}
            for idx, col in enumerate(result.keys()):
                item[col] = row[idx]
            data.append(item)
        
        # Vérifier quels éléments sont déjà transférés
        transferred_items = []
        if table_name == 'CLIENT':
            primary_key = 'id_client'
        elif table_name == 'PRODUIT':
            primary_key = 'id_produit'
        elif table_name == 'VENDEUR':
            primary_key = 'id_vendeur'
        elif table_name == 'COMMANDE':
            primary_key = 'id_commande'
        elif table_name == 'AVIS':
            primary_key = 'id_avis'
        else:  # LIGNE_COMMANDE
            primary_key = 'id_commande,id_produit'
        
        # Si la table a une seule clé primaire
        if ',' not in primary_key:
            for item in data:
                log = db_postgres_session.query(TransferLog).filter_by(
                    source_db=db_name,
                    source_table=table_name,
                    source_id=item[primary_key]
                ).first()
                
                if log:
                    transferred_items.append(item[primary_key])
        else:  # Pour les tables à clé composite (LIGNE_COMMANDE)
            keys = primary_key.split(',')
            for item in data:
                # Pour LIGNE_COMMANDE, on concatène les clés pour l'ID source
                combined_id = f"{item[keys[0]]}-{item[keys[1]]}"
                log = db_postgres_session.query(TransferLog).filter_by(
                    source_db=db_name,
                    source_table=table_name,
                    source_id=int(item[keys[0]])  # Utiliser id_commande comme référence
                ).first()
                
                if log:
                    transferred_items.append(combined_id)
                
        return render_template('data.html', 
                               db_name=db_name, 
                               table_name=table_name, 
                               data=data, 
                               columns=mysql_tables[table_name]['columns'],
                               transferred_items=transferred_items,
                               primary_key=primary_key)
    
    except Exception as e:
        flash(f'Erreur: {str(e)}')
        return redirect(url_for('show_tables', db_name=db_name))

@app.route('/transfer', methods=['POST'])
def transfer_data():
    
    db_name = request.form.get('db_name')
    table_name = request.form.get('table_name')
    selected_ids = request.form.getlist('selected_items')
    
    if not db_name or not table_name or not selected_ids:
        flash('Paramètres manquants')
        return redirect(url_for('index'))
    
    try:
        # Configuration des sessions
        mysql_session = db_mysql_connections[db_name]
        postgres_session = db_postgres_session
        
        # Récupération des données sélectionnées
        if table_name == 'LIGNE_COMMANDE':
            # Traitement spécial pour LIGNE_COMMANDE avec clé composite
            data_to_transfer = []
            for composite_id in selected_ids:
                id_commande, id_produit = composite_id.split('-')
                query = text(f"SELECT * FROM {table_name} WHERE id_commande = :id_commande AND id_produit = :id_produit")
                result = mysql_session.execute(query, {"id_commande": id_commande, "id_produit": id_produit})
                for row in result:
                    item = {}
                    for idx, col in enumerate(result.keys()):
                        item[col] = row[idx]
                    data_to_transfer.append(item)
        else:
            # Pour les tables avec une seule clé primaire
            id_field = mysql_tables[table_name]['columns'][0]  # Premier champ = clé primaire
            placeholders = ', '.join([f':{i}' for i in range(len(selected_ids))])
            query = text(f"SELECT * FROM {table_name} WHERE {id_field} IN ({placeholders})")
            params = {str(i): int(id_val) for i, id_val in enumerate(selected_ids)}
            result = mysql_session.execute(query, params)
            
            data_to_transfer = []
            for row in result:
                item = {}
                for idx, col in enumerate(result.keys()):
                    item[col] = row[idx]
                data_to_transfer.append(item)
        
        # Transférer les données vers PostgreSQL en respectant les dépendances
        for item in data_to_transfer:
            # Vérifier si l'élément existe déjà dans le journal de transfert
            if table_name == 'LIGNE_COMMANDE':
                source_id = item['id_commande']  # Utiliser id_commande comme référence principale
                exists = postgres_session.query(TransferLog).filter_by(
                    source_db=db_name, 
                    source_table=table_name, 
                    source_id=source_id
                ).first()
            else:
                primary_key = mysql_tables[table_name]['columns'][0]
                source_id = item[primary_key]
                exists = postgres_session.query(TransferLog).filter_by(
                    source_db=db_name, 
                    source_table=table_name, 
                    source_id=source_id
                ).first()
            
            if exists:
                # Élément déjà transféré, passer au suivant
                continue
            
            # Transférer l'élément vers PostgreSQL
            model_class = mysql_tables[table_name]['class']
            
            # Traitement spécial pour LIGNE_COMMANDE (clé composite)
            if table_name == 'LIGNE_COMMANDE':
                # Vérifier si la commande et le produit existent déjà dans PostgreSQL
                cmd_log = postgres_session.query(TransferLog).filter_by(
                    source_db=db_name, 
                    source_table='COMMANDE', 
                    source_id=item['id_commande']
                ).first()
                
                prod_log = postgres_session.query(TransferLog).filter_by(
                    source_db=db_name, 
                    source_table='PRODUIT', 
                    source_id=item['id_produit']
                ).first()
                
                if not cmd_log or not prod_log:
                    flash(f"Impossible de transférer la ligne de commande: commande ou produit manquant")
                    continue
                
                # Créer nouvelle ligne de commande avec les IDs PostgreSQL
                new_item = LigneCommande(
                    id_commande=cmd_log.target_id,
                    id_produit=prod_log.target_id,
                    quantite=item['quantite'],
                    remise=item['remise']
                )
                
                postgres_session.add(new_item)
                postgres_session.flush()
                
                # Enregistrer le transfert
                log_entry = TransferLog(
                    source_db=db_name,
                    source_table=table_name,
                    source_id=item['id_commande'],  # Utiliser id_commande comme référence
                    target_id=new_item.id_commande
                )
                
            elif table_name == 'AVIS':
                # Vérifier si le client et le produit existent déjà dans PostgreSQL
                client_log = postgres_session.query(TransferLog).filter_by(
                    source_db=db_name, 
                    source_table='CLIENT', 
                    source_id=item['id_client']
                ).first()
                
                prod_log = postgres_session.query(TransferLog).filter_by(
                    source_db=db_name, 
                    source_table='PRODUIT', 
                    source_id=item['id_produit']
                ).first()
                
                if not client_log or not prod_log:
                    flash(f"Impossible de transférer l'avis: client ou produit manquant")
                    continue
                
                # Créer nouvel avis avec les IDs PostgreSQL
                new_item = Avis(
                    note=item['note'],
                    commentaire=item['commentaire'],
                    id_client=client_log.target_id,
                    id_produit=prod_log.target_id
                )
                
                postgres_session.add(new_item)
                postgres_session.flush()
                
                # Enregistrer le transfert
                log_entry = TransferLog(
                    source_db=db_name,
                    source_table=table_name,
                    source_id=item['id_avis'],
                    target_id=new_item.id_avis
                )
                
            elif table_name == 'COMMANDE':
                # Vérifier si le client et le vendeur existent déjà dans PostgreSQL
                client_log = postgres_session.query(TransferLog).filter_by(
                    source_db=db_name, 
                    source_table='CLIENT', 
                    source_id=item['id_client']
                ).first()
                
                vendeur_log = postgres_session.query(TransferLog).filter_by(
                    source_db=db_name, 
                    source_table='VENDEUR', 
                    source_id=item['id_vendeur']
                ).first()
                
                if not client_log or not vendeur_log:
                    flash(f"Impossible de transférer la commande: client ou vendeur manquant")
                    continue
                
                # Créer nouvelle commande avec les IDs PostgreSQL
                new_item = Commande(
                    date_commande=item['date_commande'],
                    statut=item['statut'],
                    id_client=client_log.target_id,
                    id_vendeur=vendeur_log.target_id
                )
                
                postgres_session.add(new_item)
                postgres_session.flush()
                
                # Enregistrer le transfert
                log_entry = TransferLog(
                    source_db=db_name,
                    source_table=table_name,
                    source_id=item['id_commande'],
                    target_id=new_item.id_commande
                )
                
            else:
                # Pour les tables sans dépendances (CLIENT, PRODUIT, VENDEUR)
                new_item_data = {}
                # Supprimer l'ID pour permettre l'auto-incrémentation
                primary_key = mysql_tables[table_name]['columns'][0]
                for col in mysql_tables[table_name]['columns']:
                    if col != primary_key:  # Ignorer la clé primaire
                        new_item_data[col] = item[col]
                
                new_item = model_class(**new_item_data)
                postgres_session.add(new_item)
                postgres_session.flush()  # Pour obtenir le nouvel ID
                
                # Récupérer le nouvel ID généré
                if table_name == 'CLIENT':
                    new_id = new_item.id_client
                elif table_name == 'PRODUIT':
                    new_id = new_item.id_produit
                elif table_name == 'VENDEUR':
                    new_id = new_item.id_vendeur
                
                # Enregistrer le transfert
                log_entry = TransferLog(
                    source_db=db_name,
                    source_table=table_name,
                    source_id=item[primary_key],
                    target_id=new_id
                )
            
            postgres_session.add(log_entry)
        
        # Commit des changements
        postgres_session.commit()
        flash(f"Transfert réussi pour {len(data_to_transfer)} éléments de {table_name}")
        
    except Exception as e:
        postgres_session.rollback()
        flash(f"Erreur de transfert: {str(e)}")
    
    return redirect(url_for('show_data', db_name=db_name, table_name=table_name))

if __name__ == '__main__':
    app.run(debug=True, port=5002)