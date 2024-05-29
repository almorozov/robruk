import os

file_log = os.path.abspath(os.getcwd()) + "/logs/Events.log"
file_db = os.path.abspath(os.getcwd())+"/data/robruk.db"
FLASK_APP = 'RR_app'
FLASK_ENV = 'CTFdev'
SQLALCHEMY_DATABASE_URI = 'sqlite:///'+file_db
SQLALCHEMY_TRACK_MODIFICATIONS = False
