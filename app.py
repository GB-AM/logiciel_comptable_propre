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
    forme_juridique = db.Column(db.String(100))
    representant_legal = db.Column(db.String(100))
    qualite = db.Column(db.String(100))
    adresse = db.Column(db.String(200))
    complement_adresse = db.Column(db.String(200))
    code_postal = db.Column(db.String(10))
    ville = db.Column(db.String(100))
    telephone = db.Column(db.String(20))
    mail_general = db.Column(db.String(100))
    siret = db.Column(db.String(14))
    code_ape = db.Column(db.String(5))
    nom_charge_suivi_travaux = db.Column(db.String(100))
    fonction_charge_suivi_travaux = db.Column(db.String(100))
    mail_charge_suivi_travaux = db.Column(db.String(100))
    telephone_charge_suivi_travaux = db.Column(db.String(20))
    nom_charge_suivi_compta = db.Column(db.String(100))
    fonction_charge_suivi_compta = db.Column(db.String(100))
    mail_charge_suivi_compta = db.Column(db.String(100))

class Entreprise(db.Model):
    __tablename__ = 'entreprises'
    id = db.Column(db.Integer, primary_key=True)
    nom_entreprise = db.Column(db.String(100), nullable=False)
    forme_juridique = db.Column(db.String(100))
    representant_legal = db.Column(db.String(100))
    qualite = db.Column(db.String(100))
    adresse = db.Column(db.String(200))
    complement_adresse = db.Column(db.String(200))
    code_postal = db.Column(db.String(10))
    ville = db.Column(db.String(100))
    telephone = db.Column(db.String(20))
    mail_general = db.Column(db.String(100))
    siret = db.Column(db.String(14))
    code_ape = db.Column(db.String(5))
    titre_signataire_doc = db.Column(db.String(100))
    nom_signataire_doc = db.Column(db.String(100))
    prenom_signataire_doc = db.Column(db.String(100))
    fonction_signataire_doc = db.Column(db.String(100))
    mail_signataire_doc = db.Column(db.String(100))
    telephone_signataire_doc = db.Column(db.String(20))
    titre_signataire_ar24 = db.Column(db.String(100))
    nom_signataire_ar24 = db.Column(db.String(100))
    prenom_signataire_ar24 = db.Column(db.String(100))
    fonction_signataire_ar24 = db.Column(db.String(100))
    mail_signataire_ar24 = db.Column(db.String(100))
    titre_correspondant_situations = db.Column(db.String(100))
    nom_correspondant_situations = db.Column(db.String(100))
    prenom_correspondant_situations = db.Column(db.String(100))
    mail_correspondant_situations = db.Column(db.String(100))

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
    db.create_all()  # Recrée les tables avec les nouveaux champs    

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
            try:
                df = pd.read_excel(file, engine='xlrd')
                filename = file.filename.lower()
                if 'client' in filename or 'clients' in filename:
                    print(f"Importing clients from {filename}")
                    for index, row in df.iterrows():
                        print(row.to_dict())  # Debug
                        client = Client(
                            nom_entreprise=row.get('NOM ENTREPRISE', ''),
                            forme_juridique=row.get('FORME JURIDIQUE', ''),
                            representant_legal=row.get('REPRESENTANT LEGAL', ''),
                            qualite=row.get('QUALITE', ''),
                            adresse=row.get('ADRESSE', ''),
                            complement_adresse=row.get('COMPLEMENT ADRESSE', ''),
                            code_postal=row.get('CODE POSTAL', ''),
                            ville=row.get('VILLE', ''),
                            telephone=row.get('TELEPHONE', ''),
                            mail_general=row.get('MAIL GENERAL', ''),
                            siret=row.get('SIRET', ''),
                            code_ape=row.get('CODE APE', ''),
                            nom_charge_suivi_travaux=row.get('NOM Chargé suivi travaux', ''),
                            fonction_charge_suivi_travaux=row.get('FONCTION Chargé suivi travaux', ''),
                            mail_charge_suivi_travaux=row.get('MAIL Chargé suivi travaux', ''),
                            telephone_charge_suivi_travaux=row.get('TELEPHONE Chargé suivi travaux', ''),
                            nom_charge_suivi_compta=row.get('NOM Chargé suivi compta', ''),
                            fonction_charge_suivi_compta=row.get('FONCTION Chargé suivi compta', ''),
                            mail_charge_suivi_compta=row.get('MAIL Chargé suivi compta', '')
                        )
                        db.session.add(client)
                elif 'entreprise' in filename or 'entreprises' in filename:
                    print(f"Importing entreprises from {filename}")
                    for index, row in df.iterrows():
                        print(row.to_dict())  # Debug
                        entreprise = Entreprise(
                            nom_entreprise=row.get('NOM ENTREPRISE', ''),
                            forme_juridique=row.get('FORME JURIDIQUE', ''),
                            representant_legal=row.get('REPRESENTANT LEGAL', ''),
                            qualite=row.get('QUALITE', ''),
                            adresse=row.get('ADRESSE', ''),
                            complement_adresse=row.get('COMPLEMENT ADRESSE', ''),
                            code_postal=row.get('CODE POSTAL', ''),
                            ville=row.get('VILLE', ''),
                            telephone=row.get('TELEPHONE', ''),
                            mail_general=row.get('MAIL GENERAL', ''),
                            siret=row.get('SIRET', ''),
                            code_ape=row.get('CODE APE', ''),
                            titre_signataire_doc=row.get('TITRE signataire doc', ''),
                            nom_signataire_doc=row.get('NOM signataire doc', ''),
                            prenom_signataire_doc=row.get('PRENOM signataire doc', ''),
                            fonction_signataire_doc=row.get('FONCTION signataire doc', ''),
                            mail_signataire_doc=row.get('MAIL signataire doc', ''),
                            telephone_signataire_doc=row.get('TELEPHONE signataire doc', ''),
                            titre_signataire_ar24=row.get('TITRE signataire AR24', ''),
                            nom_signataire_ar24=row.get('NOM signataire AR24', ''),
                            prenom_signataire_ar24=row.get('PRENOM signataire AR24', ''),
                            fonction_signataire_ar24=row.get('FONCTION signataire AR24', ''),
                            mail_signataire_ar24=row.get('MAIL signataire AR24', ''),
                            titre_correspondant_situations=row.get('TITRE correspondant situations de travaux', ''),
                            nom_correspondant_situations=row.get('NOM correspondant situations de travaux', ''),
                            prenom_correspondant_situations=row.get('PRENOM correspondant situations de travaux', ''),
                            mail_correspondant_situations=row.get('MAIL correspondant situations de travaux', '')
                        )
                        db.session.add(entreprise)
                db.session.commit()
                flash('Données importées avec succès !')
            except Exception as e:
                flash(f'Erreur lors de l\'import : {str(e)}')
                print(f"Error: {str(e)}")
        return redirect(url_for('import_data'))
    return render_template('import_data.html')

@app.route('/base_clients', methods=['GET', 'POST'])
def base_clients():
    if request.method == 'POST':
        if 'delete' in request.form:
            client_id = request.form['delete']
            client = Client.query.get_or_404(client_id)
            db.session.delete(client)
            db.session.commit()
            flash('Client supprimé avec succès !')
        elif 'update' in request.form:
            client_id = request.form['client_id']
            client = Client.query.get_or_404(client_id)
            client.nom_entreprise = request.form['nom_entreprise']
            client.forme_juridique = request.form['forme_juridique']
            client.representant_legal = request.form['representant_legal']
            client.qualite = request.form['qualite']
            client.adresse = request.form['adresse']
            client.complement_adresse = request.form['complement_adresse']
            client.code_postal = request.form['code_postal']
            client.ville = request.form['ville']
            client.telephone = request.form['telephone']
            client.mail_general = request.form['mail_general']
            client.siret = request.form['siret']
            client.code_ape = request.form['code_ape']
            client.nom_charge_suivi_travaux = request.form['nom_charge_suivi_travaux']
            client.fonction_charge_suivi_travaux = request.form['fonction_charge_suivi_travaux']
            client.mail_charge_suivi_travaux = request.form['mail_charge_suivi_travaux']
            client.telephone_charge_suivi_travaux = request.form['telephone_charge_suivi_travaux']
            client.nom_charge_suivi_compta = request.form['nom_charge_suivi_compta']
            client.fonction_charge_suivi_compta = request.form['fonction_charge_suivi_compta']
            client.mail_charge_suivi_compta = request.form['mail_charge_suivi_compta']
            db.session.commit()
            flash('Client mis à jour avec succès !')
        elif 'add' in request.form:
            new_client = Client(
                nom_entreprise=request.form['nom_entreprise'],
                forme_juridique=request.form['forme_juridique'],
                representant_legal=request.form['representant_legal'],
                qualite=request.form['qualite'],
                adresse=request.form['adresse'],
                complement_adresse=request.form['complement_adresse'],
                code_postal=request.form['code_postal'],
                ville=request.form['ville'],
                telephone=request.form['telephone'],
                mail_general=request.form['mail_general'],
                siret=request.form['siret'],
                code_ape=request.form['code_ape'],
                nom_charge_suivi_travaux=request.form['nom_charge_suivi_travaux'],
                fonction_charge_suivi_travaux=request.form['fonction_charge_suivi_travaux'],
                mail_charge_suivi_travaux=request.form['mail_charge_suivi_travaux'],
                telephone_charge_suivi_travaux=request.form['telephone_charge_suivi_travaux'],
                nom_charge_suivi_compta=request.form['nom_charge_suivi_compta'],
                fonction_charge_suivi_compta=request.form['fonction_charge_suivi_compta'],
                mail_charge_suivi_compta=request.form['mail_charge_suivi_compta']
            )
            db.session.add(new_client)
            db.session.commit()
            flash('Client ajouté avec succès !')
    clients = Client.query.all()
    return render_template('base_clients.html', clients=clients)
    
@app.route('/base_entreprises', methods=['GET', 'POST'])
def base_entreprises():
    if request.method == 'POST':
        if 'delete' in request.form:
            entreprise_id = request.form['delete']
            entreprise = Entreprise.query.get_or_404(entreprise_id)
            db.session.delete(entreprise)
            db.session.commit()
            flash('Entreprise supprimée avec succès !')
        elif 'update' in request.form:
            entreprise_id = request.form['client_id']  # Doit être 'entreprise_id' ?
            entreprise = Entreprise.query.get_or_404(entreprise_id)
            entreprise.nom_entreprise = request.form['nom_entreprise']
            # ... autres champs ...
            db.session.commit()
            flash('Entreprise mise à jour avec succès !')
        elif 'add' in request.form:
            new_entreprise = Entreprise(
                nom_entreprise=request.form['nom_entreprise'],
                # ... autres champs ...
            )
            db.session.add(new_entreprise)
            db.session.commit()
            flash('Entreprise ajoutée avec succès !')
    entreprises = Entreprise.query.all()  # Corrige la casse
    return render_template('base_entreprises.html', entreprises=entreprises)
    
if __name__ == '__main__':
    print("Démarrage de l'application...")
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
