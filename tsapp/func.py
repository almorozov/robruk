from flask import Flask
import requests
import time
from .sconfig import rteam

def create_app():
    from .sconfig import SECRET_KEY
    app = Flask(__name__)
    app.config.from_pyfile('config.py')
    app.secret_key = SECRET_KEY
    return app


def f_task_acl(task, rid, uid):
    res = False
    if rid == 2:
        res = True
    if rid == 1:
        if task.private == False or (task.uid1 == uid and task.private == True):
            res = True
    if rid == 0:
        if task.uid1 == uid:
            res = True
    return res


def f_httpreq(url):
    res = 0
    try:
        response = requests.get(url)
        if response.status_code == 200:
            res = True
        else:
            res = False
    except:
        res = False
    return res
