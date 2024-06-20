from flask import Flask, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, String, Integer, ForeignKey, Table
from sqlalchemy.orm import relationship, deferred
from flask_bcrypt import Bcrypt
from random import random, randint
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import sessionmaker
app = Flask(__name__)
bcrypt = Bcrypt(app)
#Creare baza de date
app.secret_key = 'thereisnosecretkey'  
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bazadate.db'
db = SQLAlchemy(app)
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
  parola = db.Column(db.String, nullable=False)
  def set_password(self, parola):
    self.parola = bcrypt.generate_password_hash(parola).decode('utf-8')
  def check_password(self, parola):
    return bcrypt.check_password_hash(self.parola, parola)
  nume = db.Column(db.String(80), nullable=False)
  elev = db.Column(db.Boolean)
  adresa=db.Column(db.String)
  vizibil = db.Column(db.Boolean)
  clasa = db.Column(db.String)
  linkImagineU = db.Column(db.String)
  admin = db.Column(db.Boolean)
  projects = relationship('Project', secondary=user_project_association, back_populates='users')
  
#Profil proiecte
class Project(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  nume = db.Column(db.String(80), nullable=False)
  adresaP=db.Column(db.String)
  linkImagine = db.Column(db.String, nullable=False)
  vizibil = db.Column(db.Boolean)
  creator_id = deferred(Column(Integer, ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE')))
  users = relationship('User', secondary=user_project_association, back_populates='projects')
  clasa = db.Column(db.String, nullable=False)
  avansat = db.Column(db.Boolean, nullable=False)

def calculate_user_credits(user):
  total_credits = 0
  for project in user.projects:
    if project.vizibil == True:
      association = db.session.query(user_project_association).filter_by(user_id=user.id, project_id=project.id).one()
      total_credits += association.credits
  return total_credits
#Pagina redirect
@app.before_request
def make_session_permanent():
    session.permanent = True 
@app.route('/', methods=['GET', 'POST'])
def index():
  session.pop('email', None)
  if 'email' not in session:
    return redirect('/login')
  else:
    return redirect('/home')
#Pagina principala

@app.route('/home',methods=['GET','POST'])
def home():
  if 'email' not in session:
    return redirect('/login')
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
      
    return render_template("home.html", user=user, User=User, users=users, user_list=user_list, is_first=is_first, is_last=is_last, proiecte_ins=proiecte_ins, db=db,user_project_association=user_project_association)
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
                    db.session.commit()
        
        # Get the ids of projects the user has already joined
        joined_project_ids = [project.id for project in user.projects]


        # Filter out projects the user has already joined
        available_projects = Project.query.filter(
            Project.vizibil == True,
            Project.clasa.contains(user.clasa),
            ~Project.users.any(User.id == user.id),
            ~Project.id.in_(joined_project_ids),
            user.elev == True
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
        new_user = User(email=email, parola=parola,nume=nume, elev=True, adresa = adresa, vizibil=True, clasa = clasa, linkImagineU="", admin=False)
      elif elevV=="NU":
        new_user = User(email=email, parola=parola,nume=nume, elev=False, adresa = adresa, vizibil=True, linkImagineU="", admin=False)
      new_user.set_password(parola)
      db.session.add(new_user)
      db.session.commit()

      session['email'] = email

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
      linkImagine = request.form['linkImagine']
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
      new_project = new_project = Project(nume=nume, adresaP=adresaP, linkImagine=linkImagine, vizibil=True, creator_id=user.id, clasa=clasa, avansat = avansat)
      db.session.add(new_project)
      db.session.commit()
      redirect('/home')
  return render_template('create.html')

    
@app.route('/profil/<adresa>', methods=['GET','POST'])
def user_page(adresa):
  if 'email' not in session:
    return redirect('/login')
  link=request.url
  user_pagina = User.query.filter_by(adresa=adresa).first()
  user = User.query.filter_by(email=session['email']).first()
  credite = calculate_user_credits(user_pagina)
  return render_template('user_page.html', user=user, credite=credite,user_pagina=user_pagina)

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

    user_is_creator = False
    if user.id == project.creator_id:
        user_is_creator = True

    for useri in sorted_users:
        credits = db.session.query(user_project_association).filter_by(
            user_id=useri.id, project_id=project.id
        ).first().credits

        user_data.append({
            'id': useri.id,
            'nume': useri.nume,
            'credits': credits,
        })
    return render_template('project_page.html', project=project, nume_creator=nume_creator,user_data=user_data, user_is_creator=user_is_creator, user=user)
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
            db.session.trttv5()

        return redirect('/proiect/' + project.adresaP)

# Flask route for modifying credits of a user in a project
@app.route('/modify_credits', methods=['POST'])
def modify_credits():
    if 'email' not in session:
        return redirect('/login')

    if request.method == 'POST':
        project_id = request.form.get('project_id')
        user_id = request.form.get('user_id')
        credits = int(request.form.get('credits'))  # Convert to integer

        # Retrieve the current user and project
        user = User.query.filter_by(email=session['email']).first()
        user_cred = User.query.filter_by(id=user_id).first()
        project = Project.query.get(project_id)
        # Ensure the current user is the creator of the project
        if user.id != project.creator_id:
            return redirect('/home')  # Forbidden

        db.session.query(user_project_association).filter_by(user_id=user_cred.id, project_id=project.id).update({user_project_association.c.credits: credits})
        db.session.commit()


        return redirect('/proiect/' + project.adresaP)
@app.route('/leaderboard')
def leaderboard():
    if 'email' not in session:
      return redirect('/login')
    user_curent = User.query.filter_by(email=session['email']).first()
    users = User.query.filter_by(elev=True, vizibil=True).all()
    for user in users:
        user.total_credits = calculate_user_credits(user)
    users.sort(key=lambda u: u.total_credits, reverse=True)  # Sort by credits (highest first)
    profileImage = user.linkImagineU
    if profileImage=="":
      profileImage="https://i.imgur.com/1i2ohxm.jpeg"
    return render_template('leaderboard.html', users=users,profileImage=profileImage, user_curent=user_curent)

@app.route('/actualizarImagine', methods=['POST'])
def actImg():
  if 'email' not in session:
      return redirect('/login')
  if request.method == 'POST':
    user = User.query.filter_by(email=session['email']).first()
    pozaN = request.form.get('AdresaImg')
    user.linkImagineU = pozaN
    db.session.commit()
    return redirect("/profil/"+user.adresa)
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
    user = User.query.filter_by(email=session['email']).first()
    par = request.form.get('ParolaN')
    par = bcrypt.generate_password_hash(par).decode('utf-8')
    user.parola = par
    db.session.commit()
    return redirect("/profil/"+user.adresa)
@app.route('/admin', methods=['GET','POST'])
def admin():
  if 'email' not in session:
    return redirect('/login')
  user = User.query.filter_by(email=session['email']).first()
  if user.admin==True:
    return render_template('admin.html', user=user)
  else:
    return redirect('/home')

@app.route('/finaldean', methods=['GET','POST'])
def final():
   if 'email' not in session:
    return redirect('/login')
   user = User.query.filter_by(email=session['email']).first()
   if(user.admin==True):
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
      db.session.commit()
      return redirect('/admin')
        
   

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=81)


#>>> from project import app, db
#>>> app.app_context().push()
#>>> db.configure_mappers()
#>>> db.create_all()