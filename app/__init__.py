from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from os import path, getenv
from dotenv import load_dotenv

db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
load_dotenv()

def createApp():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = getenv('SQLALCHEMY_DATABASE_URI')
    app.config['MAIL_SERVER'] = 'smtp.office365.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USERNAME'] = 'lukz@merciaschool.com'
    app.config['MAIL_PASSWORD'] = getenv('MAIL_PASSWORD')
    #will have to conceal this after
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_DEFAULT_SENDER'] = 'lukz@merciaschool.com'

    mail.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)

    from .routes import routes
    app.register_blueprint(routes, url_prefix='/')

    from .models import User
    createDatabase(app)

    login_manager = LoginManager()
    login_manager.login_view = 'routes.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app

def createDatabase(app):
    if not path.exists('app/luodingo.db'):
        with app.app_context():
            db.create_all()