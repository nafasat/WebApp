from flask import Flask,render_template, flash, redirect, url_for, session, request, logging, current_app, make_response, send_from_directory
from data import Articles
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
import os
import datetime
import random

app = Flask(__name__)
#static_url_path='')
app.debug = True

#Configure MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'redhat'
app.config['MYSQL_DB'] = 'myflaskapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# init MySQL

mysql = MySQL(app)


#Articles = Articles()


#@app.errorhandler(404)
#def error404(error):
#	return render_template('404.html')

#@app.errorhandler(500)
#def error404(error):
#	return render_template('500.html')


@app.route('/')
def index():
	return render_template('index.html')

@app.route('/Statics/<path:path>')
def Statics(path):
	return send_from_directory('Statics', path)


@app.route('/about')
def about():
	return render_template('about.html')

@app.route('/articles')
def articles():
	cur = mysql.connection.cursor()
	result = cur.execute("SELECT * FROM articles")
	articles = cur.fetchall()
	if result > 0:
		return render_template('articles.html',articles=articles)
	else:
		msg = "No Result Found"
		return render_template('articles.html',msg=msg)

	cur.close()


@app.route('/article/<string:id>')
def article(id):
	cur = mysql.connection.cursor()
	result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])
	article = cur.fetchone()
	return render_template('article.html', article=article )


class RegisterForm(Form):
    name    = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('UserName', [validators.Length(min=4, max=20)])
    email = StringField('Email_Id', [validators.Length(min=5, max=30)])
    password = PasswordField('Password', [
    	validators.DataRequired(),
    	validators.EqualTo('confirm', message='Password dont match')
    	])
    confirm = PasswordField('Confirm Password')

@app.route('/register', methods=['GET','POST'])
def register():
	form = RegisterForm(request.form)
	if request.method == 'POST' and form.validate():
		name = form.name.data
		email = form.email.data
		username = form.username.data
		password = sha256_crypt.encrypt(str(form.password.data))

		#Create Cursor 

		cur = mysql.connection.cursor()
		cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))
		mysql.connection.commit()
		cur.close()

		flash("Now you are registered and can log in",'success')

		return redirect(url_for('login'))
	return render_template('register.html',form=form)

@app.route('/login', methods=['GET','POST'])
def login():
	if request.method == 'POST':
		username = request.form['username']
		password_candidate = request.form['password']

		# create a Cursur #
		cur = mysql.connection.cursor()

		#Get UserName
		result = cur.execute("SELECT * FROM users WHERE username=%s", [username])

		if result > 0:
			#Get Store Hash
			data = cur.fetchone()
			password = data['password']
			#compare Password
			if sha256_crypt.verify(password_candidate, password):
				session['logged_in'] = True
				session['username'] = username

				flash('you are logged in','success')
				return redirect(url_for('dashboard'))

			else:
				error = 'Invalid login'
				return render_template('login.html', error=error)
			cur.close()
		else:
			error = 'Username not found'
			return render_template('login.html', error=error)

	return render_template('login.html')


def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('UnAuctorized, Please login','Danger')
			return redirect(url_for('login'))
	return wrap


@app.route('/dashboard')
@is_logged_in
def dashboard():
	#Create Cursor
	cur = mysql.connection.cursor()
	result = cur.execute("SELECT * FROM articles")
	articles = cur.fetchall()
	if result > 0:
		return render_template('dashboard.html',articles=articles)
	else:
		msg = "No Result Found"
		return render_template('dashboard.html',msg=msg)

	cur.close()

#Article Class
class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=1)])



#Add Articles
@app.route('/add_article', methods=['GET','POST'])
@is_logged_in
def add_article():
	form = ArticleForm(request.form)
	if request.method=='POST' and form.validate():
		title = form.title.data
		body = form.body.data

		cur = mysql.connection.cursor()
		#Execute 
		cur.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)", (title, body, session['username']))
		mysql.connection.commit()
		#Connection close
		cur.close()

		flash('Article Created','success')
		return redirect(url_for('dashboard'))

	return render_template('add_article.html',form=form)		


#Edit Articles
@app.route('/edit_article/<string:id>', methods=['GET','POST'])
@is_logged_in
def edit_article(id):
	#Cursor
	cur = mysql.connection.cursor()

	#Get Article by ID
	result = cur.execute("SELECT * FROM articles WHERE id = %s",[id])
	article = cur.fetchone()
	print(article)
	
	#Get Form 
	form = ArticleForm(request.form)

	#Populate Article Form
	form.title.data = article['title']
	form.body.data = article['body']
	print(form.title.data)
	print(form.body.data)

	if request.method=='POST' and form.validate():
		title = request.form['title']
		body = request.form['body']

		cur = mysql.connection.cursor()
		#Execute 
		cur.execute("UPDATE articles SET title=%s, body=%s WHERE id=%s", (title, body, id) )
		mysql.connection.commit()
		#Connection close
		cur.close()

		flash('Article Updated','success')
		return redirect(url_for('dashboard'))

	return render_template('edit_article.html',form=form)


@app.route('/logout')
def logout():
	session.clear()
	flash('you are now logged out','success')
	return redirect(url_for('login'))
#	return render_template(url_for('login'))


#Delete Article
@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
	#Create Cursor
	cur = mysql.connection.cursor()

	cur.execute("DELETE FROM articles WHERE id = %s", [id])

	mysql.connection.commit()

	cur.close()

	flash('Article Deleted','success')
	return redirect(url_for('dashboard'))


## Image Upload 


def gen_rnd_filename():
    filename_prefix = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    return '%s%s' % (filename_prefix, str(random.randrange(1000, 10000)))




@app.route('/ckupload/', methods=['POST', 'OPTIONS'])
def ckupload():
    """CKEditor file upload"""
    error = ''
    url = ''
    callback = request.args.get("CKEditorFuncNum")
    print("callback=======",callback)
    if request.method == 'POST' and 'upload' in request.files:
        fileobj = request.files['upload']
        fname, fext = os.path.splitext(fileobj.filename)
        rnd_name = '%s%s' % (gen_rnd_filename(), fext)
        filepath = os.path.join(current_app.static_folder, 'upload', rnd_name)
        dirname = os.path.dirname(filepath)
        if not os.path.exists(dirname):
            try:
                os.makedirs(dirname)
            except:
                error = 'ERROR_CREATE_DIR'
        elif not os.access(dirname, os.W_OK):
            error = 'ERROR_DIR_NOT_WRITEABLE'
        if not error:
            fileobj.save(filepath)
            url = url_for('static', filename='%s/%s' % ('upload', rnd_name))
    else:
        error = 'post error'
    res = """<script type="text/javascript"> 
             window.parent.CKEDITOR.tools.callFunction(%s, '%s', '%s');
             </script>""" % (callback, url, error)
    response = make_response(res)
    response.headers["Content-Type"] = "text/html"
    print("Errror",res)
    return response



if __name__ == '__main__':
	app.secret_key='secret123'
	app.run()
