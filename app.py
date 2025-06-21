from flask import Flask, render_template, request, redirect, session, jsonify, make_response, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, String, Integer, ForeignKey, Table
from sqlalchemy.orm import relationship, deferred
from flask_bcrypt import Bcrypt
from random import random, randint, choice
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from weasyprint import HTML
import io
import os
from PIL import Image
import base64
import uuid
from uuid import uuid4
import pymysql
app = Flask(__name__)
bcrypt = Bcrypt(app)
#DATABASE_URI = f'mysql+mysqldb://mihai:karaboga@192.168.100.195/vartrack?charset=utf8mb4'
#DATABASE_URI = f'mysql+mysqldb://mihai:Var2.0team@34.89.193.177/vartrack?charset=utf8mb4'
DATABASE_URI = f'mysql+pymysql://root:Var2.0team@localhost/vartrack'
# configuration
app.config["SECRET_KEY"] = "Var2.0team"
app.config['UPLOAD_FOLDER'] = "/var/www/vartrack/images"
#app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
app.config['SQLALCHEMY_DATABASE_URI'] =DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]= True
db = SQLAlchemy(app)
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
#Tabel Conexiune User - Project
user_project_association = Table(
    'user_project_association',
    db.Model.metadata,
    Column('user_id', Integer, ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE')),
    Column('project_id', Integer, ForeignKey('project.id', ondelete='CASCADE', onupdate='CASCADE')),
    Column('credits', Integer,default=0)
)

#Profil Elevi si Profesori
class User(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  email = db.Column(db.String(80), unique=True, nullable=False)
  parola = db.Column(db.String(80), nullable=False)
  def set_password(self, parola):
    self.parola = bcrypt.generate_password_hash(parola).decode('utf-8')
  def check_password(self, parola):
    return bcrypt.check_password_hash(self.parola, parola)
  nume = db.Column(db.String(80), nullable=False)
  elev = db.Column(db.Boolean)
  adresa=db.Column(db.String(200))
  vizibil = db.Column(db.Boolean)
  clasa = db.Column(db.String(5))
  profile_image = db.Column(db.String(30))
  admin = db.Column(db.Boolean)
  verificare = db.Column(db.Boolean)
  video = db.Column(db.Boolean)

  projects = relationship('Project', secondary=user_project_association, back_populates='users')

#Profil proiecte
class Project(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  nume = db.Column(db.String(80), nullable=False)
  adresaP=db.Column(db.String(200))
  imgProiect = db.Column(db.String(60))
  vizibil = db.Column(db.Boolean)
  creator_id = deferred(Column(Integer, ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE')))
  users = relationship('User', secondary=user_project_association, back_populates='projects')
  clasa = db.Column(db.String(200), nullable=False)
  avansat = db.Column(db.Boolean)
  nr_prezente = db.Column(db.Integer)
  inscriere = db.Column(db.Boolean)
  adauga = db.Column(db.Boolean)

class Credite(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    user_id=db.Column(db.Integer, nullable=False)
    project_id=db.Column(db.Integer, nullable=False)
    credit1=db.Column(db.Integer,nullable=False)
    credit2=db.Column(db.Integer,nullable=False)
    credit3=db.Column(db.Integer,nullable=False)
    credit4=db.Column(db.Integer)
    credit5=db.Column(db.Integer)

class Prezenta(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  count = db.Column(db.Integer, nullable=False)
  user_id = db.Column(db.Integer, nullable=False)
  project_id = db.Column(db.Integer, nullable=False)
  prezent = db.Column(db.Boolean, nullable=False)

def calculate_user_credits(user):
  total_credits = 0
  for project in user.projects:
    if project.vizibil == True:
      association = db.session.query(user_project_association).filter_by(user_id=user.id, project_id=project.id).one()
      total_credits += association.credits
  return total_credits

@app.route('/get_profile_image/<user_id>')
def get_profile_image(user_id):
    user = User.query.get(user_id)
    if user and user.profile_image:
        encoded_image = user.profile_image
        decoded_image = base64.b64decode(encoded_image)
        response = make_response(decoded_image)
        response.mimetype = 'image/png'  # Replace with actual image format
        return response
def decode_image_and_store(image_file):
    try:
        image = Image.open(image_file)  # Use Pillow's Image.open
        image = image.convert('RGB')  # Convert to RGB format (optional)
        image_data = image.tobytes()
        encoded_image = base64.b64encode(image_data).decode('utf-8')
        # ... (code to store encoded_image in database) ...
        return encoded_image
    except Exception as e:
        print("Error decoding image:", e)
        return None

#Pagina redirect
@app.before_request
def make_session_permanent():
    session.permanent = True
@app.route('/', methods=['GET', 'POST'])
def index():
  #session.pop('email', None)
  if 'email' not in session:
    return redirect('/login')
  else:
    return redirect('/home')
#Pagina principala

@app.route('/home',methods=['GET','POST'])
def home():
  if 'email' not in session:
    return redirect('/login')
  #session.pop('email',None)
  user = User.query.filter_by(email=session['email']).first()
  if user.elev==True:
    users = User.query.filter_by(elev=True, vizibil=True).all()
    for user in users:
      user.total_credits = calculate_user_credits(user)
    users.sort(key=lambda u: u.total_credits, reverse=True)
    user = User.query.filter_by(email=session['email']).first()
    is_first = False
    is_last = False
    user_index = users.index(user)

    if user_index == 0:
      is_first = True

    if user_index == len(users) - 1:
      is_last = True
    user_list = []

    if user_index > 0:
      user_behind = users[user_index - 1]
      user_list.append(user_behind)

    if user_index < len(users) - 1:
      user_after = users[user_index + 1]
      user_list.append(user_after)
    user_list.append(user)
    user_projects = user.projects
    proiecte_ins=[]
    for proiect in user_projects:
      if proiect.vizibil==True:
        proiecte_ins.append(proiect)
    elevi_in_fata=[]
    elev_random=None
    index=users.index(user)
    if index:
        if index!=0:
            for  i in range(0,index):
                elevi_in_fata.append(users[i])
            elev_random=choice(elevi_in_fata)
    return render_template("home.html", user=user, User=User, users=users, user_list=user_list, is_first=is_first, is_last=is_last, proiecte_ins=proiecte_ins, db=db,user_project_association=user_project_association,elevi_in_fata=elevi_in_fata, elev_random=elev_random)
  if user.elev==False:
    proiecte_ins = Project.query.filter(Project.vizibil == True, Project.creator_id == user.id)
    return render_template("home.html", user=user, User=User, proiecte_ins=proiecte_ins, db=db,user_project_association=user_project_association)


@app.route('/proiecte', methods=['GET', 'POST'])
def proiecte():
    if 'email' not in session:
        return redirect('/login')

    user = User.query.filter_by(email=session['email']).first()

    if user.elev == True:
        if request.method == 'POST':
            project_id_to_join = request.form.get('join_project_id')
            if project_id_to_join:
                project_to_join = db.session.get(Project, project_id_to_join)
                if project_to_join and user not in project_to_join.users:
                    project_to_join.users.append(user)
                    if project_to_join.avansat==False:
                        prezenta=project_to_join.nr_prezente
                        if prezenta!=0:
                            for i in range(1,prezenta+1):
                                new_prezenta = Prezenta(count=i, user_id=user.id, project_id=project_to_join.id, prezent=False)
                                db.session.add(new_prezenta)
                        new_credite=Credite(user_id=user.id, project_id=project_to_join.id, credit1=0, credit2=0, credit3=0, credit4=0, credit5=0)
                        db.session.add(new_credite)
                    if project_to_join.avansat==True:
                        new_credite=Credite(user_id=user.id, project_id=project_to_join.id, credit1=0, credit2=0, credit3=0)
                        db.session.add(new_credite)
                    db.session.commit()

        # Get the ids of projects the user has already joined
        joined_project_ids = [project.id for project in user.projects]


        # Filter out projects the user has already joined
        available_projects = Project.query.filter(
            Project.vizibil == True,
            Project.clasa.contains(user.clasa),
            ~Project.users.any(User.id == user.id),
            ~Project.id.in_(joined_project_ids),
            user.elev == True,
            Project.inscriere == True
        ).all()


    return render_template('proiecte.html', user=user, available_projects=available_projects, User=User)

#Pagina logare
@app.route('/login', methods=['GET', 'POST'])
def login():
  if 'email' not in session:
    if request.method == 'POST':
      data = request.json  # Retrieve JSON data from the request
      email = data.get('email')
      parola = data.get('parola')

      user = User.query.filter_by(email=email).first()
      if not user or not user.check_password(parola):
          return render_template('login.html', error='Email sau parola gresita')

      session['email'] = email
      return jsonify({'success': 'Login successful'})
      #session.permanent = True - Mesaj de la Mihai din trecut > Nu uita sa adaugi linia cand lansezi aplicatia
      return redirect('/home')
  else:
    return redirect('/home')

  return render_template('login.html')

#Pagina inregistrare conturi
@app.route('/register', methods=['GET', 'POST'])
def register():
  if 'email' not in session:
      return redirect('/login')
  user=User.query.filter_by(email=session['email']).first()
  if user.admin==False:
      return redirect('/home')
  if request.method == 'POST':
      print("Form data:", request.form)
      email = request.form['email']
      parola = request.form['parola']
      nume = request.form['nume']
      elevV = request.form['elev']
      adr = bcrypt.generate_password_hash(nume+str(randint(1, 1000))).decode('utf-8')
      adresa=adr.replace("/","$")
      adresa=adresa.replace("/","$")
      if 'clasa' in request.form:
        clasa = request.form['clasa']
      else:
        clasa = None
      if elevV == "DA":
        new_user = User(email=email, parola=parola,nume=nume, elev=True, adresa = adresa, vizibil=True, clasa = clasa, admin=False, verificare=False)
      elif elevV=="NU":
        new_user = User(email=email, parola=parola,nume=nume, elev=False, adresa = adresa, vizibil=True, admin=False, verificare=False)
      new_user.set_password(parola)
      db.session.add(new_user)
      db.session.commit()

      #session['email'] = email

  return render_template('register.html')

@app.route('/create', methods = ['GET', 'POST'])
def create():
  if 'email' not in session:
    return redirect('/login')
  user = User.query.filter_by(email=session['email']).first()
  if user.elev == True:
    return redirect('/home')
  else:
    if request.method == 'POST':
      nume = request.form['nume']
      clasa = request.form['clasa']
      adrP = bcrypt.generate_password_hash(nume+str(randint(1, 1000))).decode('utf-8')
      adresaP = adrP.replace("/","$")
      claseSel = request.form.getlist('clasa')
      clasa = ' '.join(claseSel)
      avansatV = request.form['avansat']
      if avansatV == "avansat":
        avansat = True
      else:
        avansat = False
      if avansat == True:
        new_project = new_project = Project(nume=nume, adresaP=adresaP, vizibil=True, creator_id=user.id, clasa=clasa, avansat = avansat, inscriere=True, adauga=False)
      else:
        new_project = new_project = Project(nume=nume, adresaP=adresaP, vizibil=True, creator_id=user.id, clasa=clasa, avansat = avansat, nr_prezente=0, inscriere=True, adauga=False)
      db.session.add(new_project)
      db.session.commit()
      redirect('/home')
  return render_template('create.html', user = user)
@app.route('/profil/<adresa>', methods=['GET','POST'])
def user_page(adresa):
  if 'email' not in session:
    return redirect('/login')
  link=request.url
  user_pagina = User.query.filter_by(adresa=adresa).first()
  user = User.query.filter_by(email=session['email']).first()
  credite = calculate_user_credits(user_pagina)
  if request.method=='POST':
     action=request.form.get('action')
     if action=="log":
        session.pop('email', None)
        return redirect('/login')
     if action=="video":
         user.video=not(user.video)
         db.session.commit()
         return render_template('user_page.html',user=user,credite=credite,user_pagina=user_pagina,User=User,db=db,user_project_association=user_project_association)

  return render_template('user_page.html', user=user, credite=credite,user_pagina=user_pagina, User=User, db=db,user_project_association=user_project_association)

@app.route('/proiect/<adresaP>', methods=['GET', 'POST', 'DELETE', 'PUT'])
def project_page(adresaP):
    if 'email' not in session:
        return redirect('/login')
    project = Project.query.filter_by(adresaP=adresaP).first()
    user = User.query.filter_by(email=session['email']).first()
    nume_creator = User.query.get(project.creator_id).nume
    users = project.users
    sorted_users = sorted(users, key=lambda user: user.nume)
    user_data = []
    useri_available = []
    toti = User.query.filter_by(elev=True, vizibil=True).all()
    for elev in toti:
        if elev.clasa in project.clasa and elev not in project.users:
            useri_available.append(elev)
    useri_available = sorted(useri_available, key=lambda user: user.clasa)
    user_is_creator = False
    if user.id == project.creator_id:
        user_is_creator = True

    for useri in sorted_users:
        credits = db.session.query(user_project_association).filter_by(
            user_id=useri.id, project_id=project.id
        ).first().credits
        prezente = Prezenta.query.filter_by(user_id=useri.id, project_id=project.id).all()
        user_data.append({
            'id': useri.id,
            'nume': useri.nume,
            'credits': credits,
            'prezente':prezente,
        })
    if request.method== 'POST':
        user_id = request.form.get("user_id")
        for i in range(1, project.nr_prezente + 1):
            checkbox = str(i)
            if checkbox in request.form:
                prezenta = Prezenta.query.filter_by(user_id=user_id, project_id=project.id, count=i).first()
                prezenta.prezent=True
            else:
                prezenta = Prezenta.query.filter_by(user_id=user_id, project_id=project.id, count=i).first()
                prezenta.prezent=False
        db.session.commit()

    return render_template('project_page.html', project=project, nume_creator=nume_creator,user_data=user_data, user_is_creator=user_is_creator, user=user, Credite=Credite, useri_available=useri_available)
@app.route('/kick_user', methods=['POST'])
def kick_user():
    if 'email' not in session:
        return redirect('/login')

    if request.method == 'POST':
        project_id = request.form.get('project_id')
        user_id = request.form.get('user_id')

        # Retrieve the current user and project
        user = User.query.filter_by(email=session['email']).first()
        project = Project.query.get(project_id)

        # Ensure the current user is the creator of the project
        if user.id != project.creator_id:
            return redirect('/home')  # Forbidden

        # Retrieve the user to be kicked and remove them from the project
        user_to_kick = User.query.get(user_id)
        if user_to_kick in project.users:
            project.users.remove(user_to_kick)
            if project.avansat==False:
                prezente = project.nr_prezente
                for i in range(1,prezente+1):
                    prezenta = Prezenta.query.filter_by(count=i, user_id=user_to_kick.id, project_id=project.id).first()
                    db.session.delete(prezenta)
            credite=Credite.query.filter_by(project_id=project.id, user_id=user_to_kick.id).first()
            db.session.delete(credite)
            db.session.commit()

        return redirect('/proiect/' + project.adresaP)

# Flask route for modifying credits of a user in a project
@app.route('/modify_credits', methods=['POST'])
def modify_credits():
    if 'email' not in session:
        return redirect('/login')

    if request.method == 'POST':
        project_id = request.form.get('project_id')
        user_id = request.form.get('user_id')
        project = Project.query.get(project_id)
        user = User.query.filter_by(email=session['email']).first()
        if user.id != project.creator_id:
            return redirect('/home')
        if project.avansat==False:
            user_cred = User.query.filter_by(id=user_id).first()
            credit1=int(request.form.get('credit1'))
            credit2=int(request.form.get('credit2'))
            credit3=int(request.form.get('credit3'))
            credit4=int(request.form.get('credit4'))
            credit5=int(request.form.get('credit5'))
            credit_obj= Credite.query.filter_by(user_id=user_cred.id, project_id=project.id).first()

            credit_obj.credit1=credit1
            credit_obj.credit2=credit2
            credit_obj.credit3=credit3
            credit_obj.credit4=credit4
            credit_obj.credit5=credit5

            credits= credit1 + credit2 +credit3 + credit4 + credit5
            db.session.query(user_project_association).filter_by(user_id=user_cred.id, project_id=project.id).update({user_project_association.c.credits: credits})
            db.session.commit()
        if project.avansat==True:
            user_cred = User.query.filter_by(id=user_id).first()
            credit1=int(request.form.get('credit1'))
            credit2=int(request.form.get('credit2'))
            credit3=int(request.form.get('credit3'))
            credit_obj= Credite.query.filter_by(user_id=user_cred.id, project_id=project.id).first()

            credit_obj.credit1=credit1
            credit_obj.credit2=credit2
            credit_obj.credit3=credit3

            credits= credit1 + credit2 +credit3
            db.session.query(user_project_association).filter_by(user_id=user_cred.id, project_id=project.id).update({user_project_association.c.credits: credits})
            db.session.commit()


        return redirect('/proiect/' + project.adresaP)

@app.route('/nrPrezenteAct', methods=['POST'])
def nrPrezente():
    if 'email' not in session:
        return redirect('/login')

    if request.method == 'POST':
        project_id = request.form.get('project_id')
        project = Project.query.get(project_id)
        user = User.query.filter_by(email=session['email']).first()
        prezenta_old=project.nr_prezente
        prezenta_old=int(prezenta_old)
        prezenta = request.form.get('prezente')
        prezenta=int(prezenta)
        users = project.users
        if prezenta>6:
            prezenta=6
        # Ensure the current user is the creator of the project
        if user.id != project.creator_id:
            return redirect('/home')  # Forbidden
        project.nr_prezente = prezenta
        if prezenta > prezenta_old:
            for elev in users:
                for i in range(prezenta_old+1,prezenta+1):
                    new_prezenta = Prezenta(count=i, user_id=elev.id, project_id=project_id, prezent=False)
                    db.session.add(new_prezenta)
        if prezenta < prezenta_old:
            for elev in users:
                for i in range(prezenta+1, prezenta_old+1):
                    prezente=Prezenta.query.filter_by(count=i, user_id=elev.id, project_id=project_id).first()
                    db.session.delete(prezente)
        db.session.commit()


        return redirect('/proiect/' + project.adresaP)
@app.route('/leaderboard')
def leaderboard():
    if 'email' not in session:
      return redirect('/login')
    user_curent = User.query.filter_by(email=session['email']).first()
    users = User.query.filter_by(elev=True, vizibil=True).all()
    for userC in users:
        userC.total_credits = calculate_user_credits(userC)
    users.sort(key=lambda u: u.total_credits, reverse=True)  # Sort by credits (highest first)
    return render_template('leaderboard.html', users=users, user_curent=user_curent)

@app.route('/actualizarImagine', methods=['POST'])
def actImg():
    if 'email' not in session:
        return redirect('/login')

    if request.method == 'POST':
        user = User.query.filter_by(email=session['email']).first()

        if 'image-upload' in request.files:
            image_file = request.files['image-upload']
            if image_file.filename != '':
                # Create a unique filename based on the user's ID and a UUID
                filename = f"{user.id}.jpg"  # Adjust the extension as needed
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)  # Replace with your desired upload folder

                # Delete the existing file if it exists
                if os.path.exists(image_path):
                    os.remove(image_path)

                # Save the image to the specified folder
                image_file.save(image_path)

                # Update the user's profile_image attribute with the image's location (relative to the upload folder)
                user.profile_image = filename
                db.session.commit()

                # Redirect to the user's profile page
                return redirect("/profil/" + user.adresa)

    return redirect("/profil/" + user.adresa)

# Route to serve the image
@app.route('/images/<filename>')
def serve_image(filename):
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(image_path):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
@app.route('/actualizarParola', methods=['POST'])
def actPar():
  if 'email' not in session:
      return redirect('/login')
  if request.method == 'POST':
    user = User.query.filter_by(email=session['email']).first()
    par = request.form.get('ParolaN')
    par = bcrypt.generate_password_hash(par).decode('utf-8')
    user.parola = par
    db.session.commit()
    return redirect("/profil/"+user.adresa)
@app.route('/actualizarImagineProiect', methods=['POST'])
def actImgPr():
  if 'email' not in session:
      return redirect('/login')
  if request.method == 'POST':
        project_id = request.form.get('project_id')
        proiect = Project.query.get(project_id)
        if 'pic-upload' in request.files:
            image_file = request.files['pic-upload']
            if image_file.filename != '':
                # Create a unique filename based on the user's ID and a UUID
                filename = f"project-{proiect.id}.jpg"  # Adjust the extension as needed
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)  # Replace with your desired upload folder

                # Delete the existing file if it exists
                if os.path.exists(image_path):
                    os.remove(image_path)

                # Save the image to the specified folder
                image_file.save(image_path)

                # Update the user's profile_image attribute with the image's location (relative to the upload folder)
                proiect.imgProiect = filename
                db.session.commit()
                return redirect("/proiect/"+proiect.adresaP)
  return redirect("/proiect/"+proiect.adresaP)
@app.route('/admin', methods=['GET','POST'])
def admin():
  if 'email' not in session:
    return redirect('/login')
  user = User.query.filter_by(email=session['email']).first()
  if user.admin==True:
    return render_template('admin.html', user=user)
  else:
    return redirect('/home')
@app.route('/verificareAdmin', methods=['GET', 'POST'])
def verificareAdmin():
   if 'email' not in session:
    return redirect('/login')
   if request.method == 'POST':
    user = User.query.filter_by(email=session['email']).first()
    if user.admin==True:
      if user.verificare == True:
        user.verificare=False
      else:
         user.verificare=True
      db.session.commit()
      return redirect('/admin')
@app.route('/finaldean', methods=['GET','POST'])
def final():
   if 'email' not in session:
    return redirect('/login')
   if request.method == 'POST':
    user = User.query.filter_by(email=session['email']).first()
    if(user.admin==True and user.verificare==True):
      users = User.query.filter_by(elev=True, vizibil=True).all()
      projects = Project.query.filter_by(vizibil=True).all()
      for elev in users:
        if(elev.clasa=="9A"):
          elev.clasa="10A"
        elif(elev.clasa=="9B"):
          elev.clasa="10B"
        elif(elev.clasa=="10A"):
          elev.clasa="11A"
        elif(elev.clasa=="10B"):
          elev.clasa="11B"
        elif(elev.clasa=="11A"):
          elev.clasappa="12A"
        elif(elev.clasa=="11B"):
          elev.clasa="12B"
        elif(elev.clasa=="12A" or elev.clasa=="12B"):
          elev.vizibil=False
      for proiect in projects:
         proiect.vizibil=False
      user.verificare=False
      db.session.commit()
      return redirect('/admin')
   return redirect('/admin')
@app.route('/exportDate', methods=['GET','POST'])
def export():
  if 'email' not in session:
    return redirect('/login')
  if request.method=='POST':
    user = User.query.filter_by(email=session['email']).first()
    if user.admin==True:
      users = User.query.filter_by(elev=True, vizibil=True).all()
      for userC in users:
        userC.total_credits = calculate_user_credits(userC)
      users.sort(key=lambda u: u.total_credits, reverse=True)

      html = render_template('export.html', users=users)
      pdf = HTML(string=html).write_pdf()
      pdf_data = io.BytesIO(pdf)

      #response = make_response(pdf_data, 200)
      response = make_response(pdf_data.getvalue(), 200)
      response.headers['Content-Type'] = 'application/pdf'
      response.headers['Content-Disposition'] = 'attachment; filename=date.pdf'
      return response
    return redirect('/admin')
@app.route('/exportPrezenta', methods=['GET','POST'])
def exportPrezenta():
  if 'email' not in session:
    return redirect('/login')
  if request.method=='POST':
    user = User.query.filter_by(email=session['email']).first()
    project_id=request.form.get("project_id")
    project = Project.query.get(project_id)
    users=project.users
    sorted_users = sorted(users, key=lambda user: user.nume)
    user_data = []
    for useri in sorted_users:
        credits = db.session.query(user_project_association).filter_by(user_id=useri.id, project_id=project.id).first().credits
        prezente = Prezenta.query.filter_by(user_id=useri.id, project_id=project.id).all()
        user_data.append({
            'nume': useri.nume,
            'credits': credits,
            'prezente':prezente,
        })
    if project.creator_id ==user.id:
      html = render_template('exportProiect.html', users=users, user_data=user_data, project=project)
      pdf = HTML(string=html).write_pdf()
      pdf_data = io.BytesIO(pdf)

      response = make_response(pdf_data.getvalue(), 200)
      response.headers['Content-Type'] = 'application/pdf'
      response.headers['Content-Disposition'] = f'attachment; filename={project.nume}.pdf'
      return response
    return redirect('/admin')

@app.route('/program', methods=['GET','POST'])
def program():
    if 'email' not in session:
        return redirect('/login')
    user = User.query.filter_by(email=session['email']).first()
    return render_template('program.html', user=user)
@app.route('/finalDeAnProiect', methods=['GET','POST'])
def fnproiect():
    if 'email' not in session:
        return redirect('/login')
    if request.method == 'POST':
        project_id = request.form.get('project_id')
        project = Project.query.get(project_id)
        users = project.users
        if project.avansat==False:
            for elev in users:
                credite_obj = Credite.query.filter_by(user_id=elev.id, project_id=project.id).first()

                if credite_obj.credit1<80:
                    credite_obj.credit1=0

                if credite_obj.credit2<80:
                    credite_obj.credit2=0

                if credite_obj.credit3<80:
                    credite_obj.credit3=0

                if credite_obj.credit4<80:
                    credite_obj.credit4=0

                if credite_obj.credit5<80:
                    credite_obj.credit5=0

                credits= credite_obj.credit1 + credite_obj.credit2 + credite_obj.credit3 + credite_obj.credit4 + credite_obj.credit5

                db.session.query(user_project_association).filter_by(user_id=elev.id, project_id=project.id).update({user_project_association.c.credits: credits})
                db.session.commit()
        if project.avansat==True:
            for elev in users:
                credite_obj = Credite.query.filter_by(user_id=elev.id, project_id=project.id).first()

                if credite_obj.credit1<80:
                    credite_obj.credit1=0

                if credite_obj.credit2<80:
                    credite_obj.credit2=0

                if credite_obj.credit3<80:
                    credite_obj.credit3=0

                credits= credite_obj.credit1 + credite_obj.credit2 + credite_obj.credit3

                db.session.query(user_project_association).filter_by(user_id=elev.id, project_id=project.id).update({user_project_association.c.credits: credits})
                db.session.commit()
    return redirect('/proiect/' + project.adresaP)
@app.route('/resetPrezente', methods=['GET','POST'])
def rstP():
    if 'email' not in session:
        return redirect('/login')
    if request.method=='POST':
        project_id=request.form.get('project_id')
        project=Project.query.filter_by(id=project_id).first()
        prezente = Prezenta.query.filter_by(project_id=project_id).all()
        for prez in prezente:
            prez.prezent=False
            db.session.commit()
        return redirect('/proiect/'+project.adresaP)

@app.route('/tech', methods=['GET','POST'])
def techSup():
    if 'email' not in session:
        return redirect('/login')
    user=User.query.filter_by(email=session['email']).first()
    if user.admin==False:
        return redirect('/home')
    if request.method=='POST':
        if user.admin==True:
            email=request.form.get('email')
            userlog = User.query.filter_by(email=email).first()
            if userlog:
                session['email']=email
                return redirect('/home')
            else:
                return redirect('/tech')
        else:
            return redirect('/home')
    return render_template('tech.html', user=user)
@app.route('/dezIns', methods=['GET','POST'])
def dzi():
    if 'email' not in session:
        return redirect('/login')
    if request.method=='POST':
        project_id = request.form.get('project_id')
        project=Project.query.filter_by(id=project_id).first()
        if project.inscriere==True:
            project.inscriere=False
        else:
            project.inscriere=True
        db.session.commit()
        return redirect('/proiect/'+project.adresaP)
@app.route('/modProj', methods=['GET','POST'])
def modProj():
    if 'email' not in session:
        return redirect('/login')
    if request.method=='POST':
        nume=request.form.get('num_proj')
        project_id=request.form.get('project_id')
        claseSel=request.form.getlist('clasa')
        clasa=' '.join(claseSel)

        project=Project.query.filter_by(id=project_id).first()

        if project.clasa!=clasa and clasa!=None:
            project.clasa=clasa
        if nume!=project.nume and nume!=None and nume!="" and nume!=" ":
            project.nume=nume

        db.session.commit()
        return redirect('/proiect/'+project.adresaP)
@app.route('/update')
def update():
    return render_template("update.html")
@app.route('/addElev', methods=['GET','POST'])
def addElev():
    if 'email' not in session:
        return redirect('/login')
    if request.method=='POST':
        project_id=request.form.get('project_id')
        user_id=request.form.get('user_id')

        project=Project.query.filter_by(id=project_id).first()
        user_add=User.query.filter_by(id=user_id).first()
        user=User.query.filter_by(email=session['email']).first()

        if user_add:
            project.users.append(user_add)
            if project.avansat==False:
                prezenta=project.nr_prezente
                if prezenta!=0:
                    for i in range(1,prezenta+1):
                        new_prezenta=Prezenta(user_id=user_add.id, project_id=project.id, count=i, prezent=False)
                        db.session.add(new_prezenta)
                new_credite=Credite(user_id=user_add.id, project_id=project.id, credit1=0, credit2=0, credit3=0, credit4=0, credit5=0)
                db.session.add(new_credite)
            if project.avansat==True:
                new_credite=Credite(user_id=user_add.id, project_id=project.id, credit1=0, credit2=0, credit3=0)
                db.session.add(new_credite)
            db.session.commit()
    return redirect('/proiect/'+project.adresaP)
@app.route('/adauga', methods=['GET','POST'])
def adauga():
    if 'email' not in session:
        return redirect('/login')
    if request.method=='POST':
        project_id=request.form.get('project_id')
        project=Project.query.filter_by(id=project_id).first()
        project.adauga=not(project.adauga)
        db.session.commit()
        return redirect('/proiect/'+project.adresaP)

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=5000)

