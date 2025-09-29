from flask import Flask, render_template, request, redirect, url_for, flash
from flask_socketio import SocketIO, emit
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import pandas as pd
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ta_cle_secrete_2025'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
socketio = SocketIO(app, cors_allowed_origins="*")

engine = create_engine('sqlite:///database.db')
Base = declarative_base()
Session = sessionmaker(bind=engine)

# Modèle Client
class Client(Base):
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True)
    nom_entreprise = Column(String)
    forme_juridique = Column(String)
    representant_legal = Column(String)
    qualite = Column(String)
    adresse = Column(String)
    complement_adresse = Column(String)
    code_postal = Column(String)
    ville = Column(String)
    telephone = Column(String)
    mail_general = Column(String)
    siret = Column(String)
    code_ape = Column(String)
    signataire_nom = Column(String)
    signataire_fonction = Column(String)
    signataire_mail = Column(String)
    marches = relationship("Marche", back_populates="client")

# Modèle Entreprise
class Entreprise(Base):
    __tablename__ = 'entreprises'
    id = Column(Integer, primary_key=True)
    nom = Column(String)
    forme_juridique = Column(String)
    representant_legal = Column(String)
    qualite = Column(String)
    adresse1 = Column(String)
    adresse2 = Column(String)
    code_postal = Column(String)
    ville = Column(String)
    telephone = Column(String)
    mail_general = Column(String)
    siret = Column(String)
    code_ape = Column(String)
    signataire_nom = Column(String)
    signataire_fonction = Column(String)
    signataire_mail = Column(String)
    montant_marche_ht = Column(Float)

# Modèle Marche
class Marche(Base):
    __tablename__ = 'marches'
    id = Column(Integer, primary_key=True)
    nom_marche = Column(String)
    intitule = Column(String)
    adresse_chantier = Column(String)
    code_postal = Column(String)
    ville = Column(String)
    montant_total_ht = Column(Float)
    client_id = Column(Integer, ForeignKey('clients.id'))
    client = relationship("Client", back_populates="marches")
    taux_tva = Column(Float, default=20.0)
    penalite_retard_execution = Column(Float, default=100)
    penalite_retard_reserves = Column(Float, default=150)
    penalite_remise_docs = Column(Float, default=151)

# Modèle Lot
class Lot(Base):
    __tablename__ = 'lots'
    id = Column(Integer, primary_key=True)
    numero_lot = Column(String)
    intitule_lot = Column(String)
    entreprise_id = Column(Integer, ForeignKey('entreprises.id'))
    montant_ht = Column(Float)
    marche_id = Column(Integer, ForeignKey('marches.id'))

# Modèle Penalite
class Penalite(Base):
    __tablename__ = 'penalites'
    id = Column(Integer, primary_key=True)
    marche_id = Column(Integer, ForeignKey('marches.id'))
    type_penalite = Column(String)
    valeur = Column(Float)
    unite = Column(String)
    minimum = Column(Float, default=0)

Base.metadata.create_all(engine)

# Routes
@app.route('/')
def accueil():
    return render_template('accueil.html')
    
@app.route('/marches')
def marches():
    session = Session()
    marches = session.query(Marche).all()
    session.close()
    return render_template('marches.html', marches=marches)

@app.route('/marche/nouveau', methods=['GET', 'POST'])
def nouveau_marche():
    session = Session()
    clients = session.query(Client).all()
    entreprises = session.query(Entreprise).all()
    session.close()
    if request.method == 'POST':
        # Ton code POST ici, indenté
        nom_marche = request.form['nom_marche']
        # ... (le reste du code POST)
        return redirect(url_for('marches'))
    return render_template('nouveau_marche.html', clients=clients, entreprises=entreprises)

@app.route('/import_data')
def import_data():
    try:
        session = Session()
        # Import Base Entreprises
        df_entreprises = pd.read_excel('Trame base entreprise.xls', sheet_name=0, header=0)
        for _, row in df_entreprises.iterrows():
            if pd.notna(row.get('NOM ENTREPRISE', '')):
                entreprise = Entreprise(
                    nom=str(row.get('NOM ENTREPRISE', '')),
                    adresse1=str(row.get('ADRESSE', '')),
                    code_postal=str(row.get('CODE POSTAL', '')),
                    ville=str(row.get('VILLE', '')),
                    telephone=str(row.get('TELEPHONE', '')),
                    mail_general=str(row.get('MAIL GENERAL', ''))
                )
                session.add(entreprise)
        # Import Clients
        df_clients = pd.read_excel('Trame base client.xls', sheet_name=0, header=0)
        for _, row in df_clients.iterrows():
            if pd.notna(row.get('NOM ENTREPRISE', '')):
                client = Client(
                    nom_entreprise=str(row.get('NOM ENTREPRISE', '')),
                    adresse=str(row.get('ADRESSE', '')),
                    code_postal=str(row.get('CODE POSTAL', '')),
                    ville=str(row.get('VILLE', '')),
                    telephone=str(row.get('TELEPHONE', '')),
                    mail_general=str(row.get('MAIL GENERAL', ''))
                )
                session.add(client)
        # Import Marché
        df_marche = pd.read_excel('Création nouveau marché.xls', sheet_name=0, header=0)
        client_nom = str(df_marche.iloc[0].get('CLIENT_Nom', '')).strip()
        client = session.query(Client).filter_by(nom_entreprise=client_nom).first()
        if not client and client_nom:
            client = Client(nom_entreprise=client_nom, adresse=str(df_marche.iloc[0].get('CLIENT_Adresse', '')).strip(), code_postal=str(df_marche.iloc[0].get('CLIENT_Code postal', '')).strip(), ville=str(df_marche.iloc[0].get('CLIENT_Ville', '')).strip(), telephone=str(df_marche.iloc[0].get('CLIENT_Téléphone fixe', '')).strip(), mail_general=str(df_marche.iloc[0].get('CLIENT_Mail général', '')).strip())
            session.add(client)
            session.flush()
        if client:
            marche = Marche(
                nom_marche=str(df_marche.iloc[0].get('Nom du marché :', '')).strip(),
                adresse_chantier=str(df_marche.iloc[2].get('Adresse chantier :', '')).strip(),
                code_postal=str(df_marche.iloc[3].get('Code postal :', '')).strip(),
                ville=str(df_marche.iloc[4].get('Ville :', '')).strip(),
                montant_total_ht=float(str(df_marche.iloc[5].get('Montant total du marché HT :', '0')).replace(' €', '').replace(',', '.')),
                client_id=client.id
            )
            session.add(marche)
            session.flush()
            for i in range(1, 20):
                numero_lot = str(df_marche.iloc[0].get(f'N° lot_{i}', '')).strip()
                intitule_lot = str(df_marche.iloc[0].get(f'Intitulé Lot_{i}', '')).strip()
                montant_ht = str(df_marche.iloc[0].get(f'Montant marché HT_{i}', '')).strip()
                if numero_lot and intitule_lot and montant_ht:
                    entreprise = session.query(Entreprise).filter_by(nom=numero_lot).first()
                    if not entreprise:
                        entreprise = Entreprise(nom=numero_lot, adresse1=marche.adresse_chantier, code_postal=marche.code_postal, ville=marche.ville)
                        session.add(entreprise)
                        session.flush()
                    lot = Lot(numero_lot=numero_lot, intitule_lot=intitule_lot, entreprise_id=entreprise.id, montant_ht=float(montant_ht.replace(' €', '')), marche_id=marche.id)
                    session.add(lot)
        session.commit()
        session.close()
        flash('Données importées avec succès !')
    except Exception as e:
        flash(f'Erreur lors de l\'import : {str(e)}')
    return redirect(url_for('accueil'))
    
import os
from flask import Flask, render_template, request, flash, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import xlrd

app = Flask(__name__)
app.secret_key = 'votre_clé_secrète_ici'  # Change ça pour une clé sécurisée
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration de la base de données
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
Base = declarative_base()

# Modèles (Client, Entreprise, Marche, etc.) - garde tes définitions existantes ici

# Routes (accueil, marches, nouveau_marche, import_data) - garde tes routes existantes ici

if __name__ == '__main__':
    print("Démarrage de l'application...")
    # Pour Render, utilise Gunicorn avec le port défini par l'environnement
    port = int(os.getenv("PORT", 5000))  # Default à 5000 si non défini
    socketio.run(app, host='0.0.0.0', port=port)