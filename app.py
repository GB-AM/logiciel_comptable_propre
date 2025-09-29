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
app.secret_key = 'votre_clé_secrète_ici'  # Change ça pour une clé sécurisée en production
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration de la base de données
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
Base = declarative_base()

# Modèles
class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    nom_entreprise = db.Column(db.String(100), nullable=False)
    adresse = db.Column(db.String(200))
    code_postal = db.Column(db.String(10))
    ville = db.Column(db.String(100))
    telephone = db.Column(db.String(20))
    mail_general = db.Column(db.String(100))

class Entreprise(db.Model):
    __tablename__ = 'entreprises'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)

class Marche(db.Model):
    __tablename__ = 'marches'
    id = db.Column(db.Integer, primary_key=True)
    nom_marche = db.Column(db.String(100), nullable=False)
    intitule = db.Column(db.String(200))
    adresse_chantier = db.Column(db.String(200))
    code_postal = db.Column(db.String(10))
    ville = db.Column(db.String(100))
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'))
    client = db.relationship('Client', backref='marches')
    montant_total_ht = db.Column(db.Float)
    taux_tva = db.Column(db.Float)
    penalites = db.relationship('Penalite', backref='marche')

class Penalite(db.Model):
    __tablename__ = 'penalites'
    id = db.Column(db.Integer, primary_key=True)
    marche_id = db.Column(db.Integer, db.ForeignKey('marches.id'))
    type = db.Column(db.String(100))
    valeur = db.Column(db.Float)
    unite = db.Column(db.String(50))
    minimum = db.Column(db.Float)

# Création de la base de données
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def index():
    return render_template('accueil.html')

@app.route('/marches')
def marches():
    marches = Marche.query.all()
    return render_template('marches.html', marches=marches)

@app.route('/marche/nouveau', methods=['GET', 'POST'])
def nouveau_marche():
    if request.method == 'POST':
        nom_marche = request.form['nom_marche']
        intitule = request.form['intitule']
        adresse_chantier = request.form['adresse_chantier']
        code_postal = request.form['code_postal']
        ville = request.form['ville']
        client_id = request.form['client_id']
        montant_total_ht = float(request.form['montant_total_ht'].replace(' ', '').replace('€', ''))
        taux_tva = float(request.form['taux_tva'])

        nouveau_marche = Marche(
            nom_marche=nom_marche,
            intitule=intitule,
            adresse_chantier=adresse_chantier,
            code_postal=code_postal,
            ville=ville,
            client_id=client_id,
            montant_total_ht=montant_total_ht,
            taux_tva=taux_tva
        )
        db.session.add(nouveau_marche)

        # Gestion des pénalités
        penalite_count = int(request.form.get('penalite_count', 1))
        for i in range(1, penalite_count + 1):
            penalite_type = request.form.get(f'penalite_type_{i}')
            if penalite_type:
                penalite = Penalite(
                    marche=nouveau_marche,
                    type=penalite_type,
                    valeur=float(request.form.get(f'penalite_{i}', 0)),
                    unite=request.form.get(f'unite_{i}', 'jour'),
                    minimum=float(request.form.get(f'minimum_{i}', 0))
                )
                db.session.add(penalite)

        db.session.commit()
        flash('Marché créé avec succès !')
        return redirect(url_for('marches'))

    clients = Client.query.all()
    entreprises = Entreprise.query.all()
    return render_template('nouveau_marche.html', clients=clients, entreprises=entreprises)

@app.route('/import_data', methods=['GET', 'POST'])
def import_data():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.xls'):
            df = pd.read_excel(file, engine='xlrd')
            filename = file.filename.lower()
            if 'client' in filename:  # Pour "Trame base client.xls"
                for index, row in df.iterrows():
                    client = Client(
                        nom_entreprise=row.get('nom_entreprise', row.get('Nom de l\'entreprise', '')),
                        adresse=row.get('adresse', ''),
                        code_postal=row.get('code_postal', ''),
                        ville=row.get('ville', ''),
                        telephone=row.get('telephone', ''),
                        mail_general=row.get('mail_general', '')
                    )
                    db.session.add(client)
            elif 'entreprise' in filename:  # Pour "Trame base entreprise.xls"
                for index, row in df.iterrows():
                    entreprise = Entreprise(nom=row.get('nom', row.get('Nom', '')))
                    db.session.add(entreprise)
            db.session.commit()
            flash('Données importées avec succès !')
        return redirect(url_for('import_data'))  # Reste sur la page d'import après succès
    return render_template('import_data.html')

@app.route('/base_clients')
def base_clients():
    clients = Client.query.all()
    return render_template('base_clients.html', clients=clients)

@app.route('/base_entreprises')
def base_entreprises():
    entreprises = Entreprise.query.all()
    return render_template('base_entreprises.html', entreprises=entreprises)
    
if __name__ == '__main__':
    print("Démarrage de l'application...")
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
