#-*- coding:utf-8 -*-
import os
import random
from flask import Flask, render_template, redirect, url_for, request, g

## import sqlalchemy
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

## import flask-login
from flask.ext.login import LoginManager, login_user, logout_user, login_required, current_user

## import hashlib
import hashlib

## import json
import json

## import pusher
import pusher

## create flask app
app = Flask(__name__)

## debug mode set true
app.debug = True

## configuration database uri. this can be changed for 'mysql' 'postgresql' and so on.
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////home/ubuntu/workspace/mydb.db'

## set a secret
app.config['SECRET_KEY'] = 'asjdfiaj49wifajds0j3' #아무 문자가 기입

## create(initialize) sqlalchemy 
db = SQLAlchemy(app)

## create login manager  로그인 매니저를 전역변수로 설정
login_manager = LoginManager()
login_manager.init_app(app)


### declare models
class User(db.Model): ## user model. 
    id = db.Column(db.Integer, primary_key=True)
    
    name = db.Column(db.VARCHAR(256))
    password = db.Column(db.VARCHAR(256))
    age = db.Column(db.Integer)
    created = db.Column(db.DateTime, default=datetime.now())
    guestbooks = db.relationship('Guestbook', backref='author', lazy='dynamic') ##릴레이션 정리 books라고 하면 컬럼이 자동으로 생김. 괄호 안에는 관계를 맺을 모델명을 스트링으로 입력. 관계를 맺을 외래키도 입력.
                                #'Guestbook은 아래 클래스와 컨벤션, author는 아래와 컨벤션.  추가적으로 backref는 author로 접근할 수 있다는 뜻
    def is_authenticated(self): #이 세 가지는 user에 있는 flask 로그인에서 제공하는 규칙. 이건 인증된 유저인지 활성활된 유저인지.. 지금 당장 쓸 거 아니니 True로
        return True
    def is_active(self):
        return True
    def get_id(self): #플라스크 호출하는 함수, 이 아이디를 가지고 세션에 저장함. 그래서 플라스크 로그인에게 알려줘야할 때 사용. 세션 체크
        return unicode(self.id)
    
class Guestbook(db.Model): ## guest book model.
    id = db.Column(db.Integer, primary_key=True)
    guest_name = db.Column(db.VARCHAR(256))
    contents = db.Column(db.Text)
    created = db.Column(db.DateTime, default=datetime.now())
    author_id = db.Column(db.Integer, db.ForeignKey('user.id')) ##'user.id가 위에서 정의한 클래스의 네임에 따라서 바뀌면 이것도 바뀌어야함.
    
## preprocess  컨트롤러 진입 전 전처리기
@login_manager.user_loader #이걸 선언하게 되면 이 아래에 있는 것들을 모든 페이지마다 호출하게 됨
def load_user(id):  #모든 페이지를 갈 때마다 user정보를 상단에도 떠야하고, 글 남길때도 있어야 하므로, 모든 페이지 첫 부분에 복붙하기 힘드므로 이렇게 선언함.
    return User.query.get(int(id)) ##위의 get_id와 같아야함 실제로는 세션에 넣었다가 가져오는데, 무튼 위에 있는 get_id를 가져옴

@app.before_request   #위에 있는거랑 한 몸이라고 봐야함 왜냐하면 전처리기로 전역변수 유저라는 전역변수를 선언하기 위함
def before_request():
    g.user = current_user ##g.은 글로벌변수로 파이썬 전역에서 사용가능
    
    
### declare controllers
## route '/'
@app.route('/', methods=['GET','POST'])
def index_page():
    if request.method == 'GET':
        ## if logined 로그인하였을 때
        if g.user.is_authenticated: ##사용자가 있으면
            return redirect(url_for('guest_book')) ## 리다이렉트를 시켜줌 
        
        ## query(get) data
        # User : model class
        # User.query : query for model 'User'
        # User.query.filter(User.age>=20).order_by(User.age.desc()) : query by filtering 'age >= 20' and order by age descending.
        users = User.query.filter(User.age>=20).order_by(User.age.desc())
        
        ## render to index.html with 'users'
        return render_template('index.html', users = users)
    elif request.method == 'POST':
        name = request.form['username']
        password = request.form['password']
        
        ## hash password 암호화
        password = hashlib.sha224(password).hexdigest()
        
        ## find user and check password
        user = User.query.filter_by(name=name, password=password).first() #필터바이만 쓰면 리스트로 여러개 가져옴. 하나만 가져오면 되므로 first
        if user: ## 사용자가 있으면
            ## session save 세션을 처리해야함
            login_user(user) ## g.session['logined']= True    이것이 true인지 확인
                             ## g.session[login_id'] = user.id  user id가 맞는지  이 두 줄을 축약해서 사용한 것이 이것!!     
            
            ## just add a item database session 
            db.session.add(user)
            ## adjust database session (actually, added)
            db.session.commit()
    ## if you're not 'get' request, just go to 'def index_page' (GET)  
    return redirect(url_for('index_page'))


## route '/signup'
@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')    
    elif request.method == 'POST':
         ## get form data (username, age)
        username = request.form['username']
        password = request.form['password']
        age = request.form['age']
        
        ## hash the password 암호화
        password = hashlib.sha224(password).hexdigest() ## 암호화
        
        ## check duplicate 중복체크를 해줘야함
        if User.query.filter_by(name=username).first(): ##중복된게 있는 경우 회원가입 시켜주면 안됨
            return redirect(url_for('signup'))
        
        ## insert data from form
        user = User(name=username, password=password, age=age, created=datetime.now())
        
        ## just add a item database session 
        db.session.add(user)
        
        ## adjust database session (actually, added)
        db.session.commit()
        
        return redirect(url_for('index_page'))
    
    
    return redirect(url_for('index_page'))

## route '/guest'
@app.route('/guest', methods=['GET','POST'])
@login_required ##각 컨트롤러 별로 권한을 설정함. 데코레이트 패턴으로 로그인 체크가 가능함. 
def guest_book():
    if request.method == 'GET':
        ## query(get) data, sort by created. (descending)
        books = Guestbook.query.order_by(Guestbook.created.desc())
        
        ## render books.html 
        return render_template('books.html', books = books)
    elif request.method == 'POST':
        
        ## get form data 데이터 폼을 가져오기
        author_id = request.form['author_id']
        guestname = request.form['guest_name']
        contents = request.form['contents']
        
        ## insert data
        guestbook = Guestbook(guest_name = guestname, contents = contents, author_id=author_id, created = datetime.now()) ##위에 가져온 것 추가하면 알아서 릴레이션 관계 설정됨
        db.session.add(guestbook)
        db.session.commit()
    
    ## redirecting...
    return redirect(url_for('guest_book'))  
    
## route '/guest/update'
@app.route('/guest/update', methods=['GET','POST'])  ##위의 게스트북과 구조가 같으므로 거의 다 복붙하고 몇 개 빼기
def guest_update():
    if request.method == 'GET':
        ## query(get) data, find book by id
        book_id = request.args['book_id']  ##북아이디를 파라미터로 가져와야함 Get으로 받으니까 쿼리스트링으로 받음
        book = Guestbook.query.get(int(book_id)) ## 리퀘스트는 다 스트링으로 와서 int로 캐스팅을 해주고 get으로 받아야함. get의 특징은 주키를 받아야한다는 특징
                                                    ## get대신에 필터바이로 해도 됨. 차이가 없음
        ## render books.html 
        ## render_template('해석할 html 이름', (html에서 쓰일 변수의 이름)=(app.py에 있는 변수의 이름), .........  )
        return render_template('book_update.html', book = book)
    elif request.method == 'POST':
        
        ## get form data
        book_id = request.form['book_id']
        author_id = request.form['author_id']
        guestname = request.form['guest_name']
        contents = request.form['contents']
        
        ## modifying
        book = Guestbook.query.get(int(book_id))  ##위와 같이 북을 가져옴. DB에서 가져옴
        book.author_id = author_id   ## 업데이트를 하기 위해 새로 받은 아이디를 넣어준다.
        book.guest_name = guestname   ##
        book.contents = contents
        
        db.session.commit()
    
    ## redirecting...
    return redirect(url_for('guest_book'))  
    
@app.route('/guest/delete')
@login_required
def guest_delete():
    book_id = request.args['book_id']
    book = Guestbook.query.get(int(book_id))
    if book:
        #Guestbook.query.filter_by(id=book.id).delete()
        db.session.delete(book)
        db.session.commit()
        
    return redirect(url_for('guest_book'))    
    
@app.route('/map', methods=['GET','POST'])
def guest_map():
    if request.method == 'GET':
        return render_template('map.html')
    elif request.method == 'POST':
        return redirect(url_for('index_page'))  
        
@app.route('/chatting', methods=['GET','POST'])
def guest_chatting():
    if request.method == 'GET':
        return render_template('chatting.html')
    elif request.method == 'POST':
        return redirect(url_for('index_page'))          
    
## likes request
@app.route('/like')
def like_guest():
    ### /like?id=2
    guest_id = request.args['id']
    book = Guestbook.query.filter_by(id=guest_id).first()
    book.likes = book.likes + 1
    db.session.commit()
    
    return json.dumps({   ## return json.dumps(book) 이것도 가능
        'id':book.id,
        'likes':book.likes ## 불리언, 배열, 숫자, 문자 넣을 수 있음.
    })    
        
## chat message send
@app.route('/message', methods=['POST'])
def send_message():
    p = pusher.Pusher(
      app_id='174871',
      key='fef0e0c6ceda0fa483aa',
      secret='1eccc53fe745274eaa84',
      ssl=True,
      port=443
    )
    p.trigger('chat', 'new_message', {'message': request.form['message']})
    
    return json.dumps({
        'success':True
        })    
    
@app.route('/logout') ##로그아웃 구현
@login_required
def logout():
    logout_user()
    
    return redirect(url_for('index_page'))
    

        
### run flask app
if __name__ == '__main__':
    app.run(host=os.getenv('IP','0.0.0.0'), port=int(os.getenv('PORT',8080)))