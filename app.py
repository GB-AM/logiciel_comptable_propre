from flask import Flask, render_template, request, redirect, url_for, flash
from flask_socketio import SocketIO, emit
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
import os
import pandas as pd

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ta_cle_secrete_2025'
socketio = SocketIO(app, cors_allowed_origins="*")

engine = create_engine('sqlite:///database.db')
Base = declarative_base()
Session = sessionmaker(bind=engine)

class Client(Base):
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True)
    nom_entreprise = Column(String)
    adresse = Column(String)
    code_postal = Column(String)
    ville = Column(String)
    telephone = Column(String)
    mail_general = Column(String)

class Entreprise(Base):
    __tablename__ = 'entreprises'
    id = Column(Integer, primary_key=True)
    nom = Column(String)
    adresse1 = Column(String)
    code_postal = Column(String)
    ville = Column(String)
    telephone = Column(String)
    mail_general = Column(String)
    montant_marche_ht = Column(Float)

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
    taux_tva = Column(Float, default=20.0)  # Nouveau champ pour TVA
    penalite_retard_execution = Column(Float, default=100)
    penalite_retard_reserves = Column(Float, default=150)
    penalite_remise_docs = Column(Float, default=151)

class Lot(Base):
    __tablename__ = 'lots'
    id = Column(Integer, primary_key=True)
    numero_lot = Column(String)
    intitule_lot = Column(String)
    entreprise_id = Column(Integer, ForeignKey('entreprises.id'))
    montant_ht = Column(Float)
    marche_id = Column(Integer, ForeignKey('marches.id'))

class Penalite(Base):
    __tablename__ = 'penalites'
    id = Column(Integer, primary_key=True)
    marche_id = Column(Integer, ForeignKey('marches.id'))
    type_penalite = Column(String)
    valeur = Column(Float)  # Peut être en €/jour ou fraction
    unite = Column(String)  # 'jour' ou 'fraction'
    minimum = Column(Float, default=0)

Base.metadata.create_all(engine)

@app.route('/')
def accueil():
    return render_template('accueil.html')

@app.route('/marche/nouveau', methods=['GET', 'POST'])
def nouveau_marche():
    session = Session()
    clients = session.query(Client).all()
    entreprises = session.query(Entreprise).all()
    session.close()
    if request.method == 'POST':
        # Code inchangé
    return render_template('nouveau_marche.html', clients=clients, entreprises=entreprises)

@app.route('/marche/nouveau', methods=['GET', 'POST'])
def nouveau_marche():
    session = Session()
    clients = session.query(Client).all()
    entreprises = session.query(Entreprise).all()
    if request.method == 'POST':
        nom_marche = request.form['nom_marche']
        intitule = request.form['intitule']
        adresse_chantier = request.form['adresse_chantier']
        code_postal = request.form['code_postal']
        ville = request.form['ville']
        client_id = int(request.form['client_id'])
        taux_tva = float(request.form.get('taux_tva', 20))
        # Calcul montant total HT à partir des lots
        montant_total_ht = 0
        for i in range(1, 51):  # Jusqu'à 50 lots
            montant_ht = request.form.get(f'montant_ht_{i}')
            if montant_ht and montant_ht.strip():
                montant_total_ht += float(montant_ht)
        nouveau_marche = Marche(
            nom_marche=nom_marche, intitule=intitule, adresse_chantier=adresse_chantier,
            code_postal=code_postal, ville=ville, montant_total_ht=montant_total_ht,
            client_id=client_id, taux_tva=taux_tva
        )
        session.add(nouveau_marche)
        session.flush()
        # Ajouter pénalités
        penalite_types = [
            'Retard dans le commencement des travaux', 'Retard dans l’achèvement des travaux',
            'Retard ou absence aux réunions', 'Absence d’encadrement', 'Défaut d’exécution',
            'Retard sur communication du PPSPS', 'Retard sur remise de documents',
            'Retard sur communication des devis TMA', 'Non-respect des règles de sécurité',
            'Provisoires pour malfaçons', 'Non remise de documents après exécution',
            'Retard dans la levée des réserves d’OPR', 'Retard dans la levée des réserves de réception',
            'Non-présentation de la carte d’identification professionnelle', 'Retard sur ordres donnés',
            'Non-respect des surfaces dédiées aux logements', 'Non-respect de label ou certification',
            'Non-atteinte des performances des équipements', 'Retard dans la libération du terrain',
            'Sous-traitance non-déclarée', 'Défaut de nettoyage'
        ]
        for penalite_type in penalite_types:
            valeur = request.form.get(f'penalite_{penalite_type.replace(" ", "_")}')
            unite = request.form.get(f'unite_{penalite_type.replace(" ", "_")}')
            minimum = request.form.get(f'minimum_{penalite_type.replace(" ", "_")}')
            if valeur and unite:
                penalite = Penalite(
                    marche_id=nouveau_marche.id,
                    type_penalite=penalite_type,
                    valeur=float(valeur),
                    unite=unite,
                    minimum=float(minimum) if minimum else 0
                )
                session.add(penalite)
        # Ajouter lots
        for i in range(1, 51):
            numero_lot = request.form.get(f'numero_lot_{i}')
            intitule_lot = request.form.get(f'intitule_lot_{i}')
            entreprise_nom = request.form.get(f'entreprise_nom_{i}')
            montant_ht = request.form.get(f'montant_ht_{i}')
            if numero_lot and intitule_lot and montant_ht:
                entreprise = session.query(Entreprise).filter_by(nom=entreprise_nom).first()
                if not entreprise:
                    entreprise = Entreprise(nom=entreprise_nom, adresse1=adresse_chantier, code_postal=code_postal, ville=ville)
                    session.add(entreprise)
                    session.flush()
                lot = Lot(numero_lot=numero_lot, intitule_lot=intitule_lot, entreprise_id=entreprise.id, montant_ht=float(montant_ht), marche_id=nouveau_marche.id)
                session.add(lot)
        session.commit()
        session.close()
        flash('Nouveau marché créé avec succès !')
        return redirect(url_for('marches'))
    session.close()
    return render_template('nouveau_marche.html', clients=clients, entreprises=entreprises)

@app.route('/marche/<int:marche_id>')
def marche_detail(marche_id):
    session = Session()
    marche = session.query(Marche).get(marche_id)
    if marche:
        lots = session.query(Lot).filter_by(marche_id=marche_id).all()
        penalites = session.query(Penalite).filter_by(marche_id=marche_id).all()
        session.close()
        return render_template('marche_detail.html', marche=marche, lots=lots, penalites=penalites)
    session.close()
    return redirect(url_for('marches'))

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
        session.commit()
        session.close()
        flash('Données importées avec succès !')
    except Exception as e:
        flash(f'Erreur lors de l\'import : {str(e)}')
    return redirect(url_for('accueil'))

if __name__ == '__main__':
    socketio.run(app, debug=True)