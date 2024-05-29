from flask import Flask, render_template, render_template_string, request, url_for, redirect, flash, make_response, has_request_context
from sqlalchemy import and_, or_, not_
from datetime import datetime, date
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
import logging
from flask.logging import default_handler
from logging.handlers import RotatingFileHandler
from flask_paginate import Pagination, get_page_parameter
import time
import os

from .models import TS_Task, TS_User, db
from .sconfig import rteam, team, hostrr
from .config import file_log
from .func import *

#For logs
class RequestFormatter(logging.Formatter):
    def format(self, record):
        if has_request_context():
            record.url = request.url
            record.remote_addr = request.remote_addr
        else:
            record.url = None
            record.remote_addr = None
        return super().format(record)

formatter = RequestFormatter('[%(asctime)s] [%(levelname)s] from %(remote_addr)s req: %(url)s > %(message)s')

#Init App
app = create_app()
db.init_app(app)
manager = LoginManager(app)
if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
handler = RotatingFileHandler(file_log, maxBytes=1048576, backupCount=10)
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)
app.logger.addHandler(handler)


@manager.user_loader
def load_user(user_id):
    return TS_User.query.get(user_id)


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/myprofile')
@login_required
def myprofile():
    app.logger.info('[FUNC] [/MyProfile] [Succeess] User:<%s>',current_user.login)
    rid = current_user.rid
    return render_template("myprofile.html", user=current_user, rteam=rteam, rid=rid)


@app.route('/login', methods=['POST','GET'])
def login():
    if request.method == "POST":
        ulogin = request.form['login']
        upassword = request.form['password']
        user = TS_User.query.filter_by(login=ulogin).first()
        if user and check_password_hash(user.password, upassword):
            login_user(user)
            resp = make_response(redirect(url_for('myprofile')))
            resp.set_cookie('rid', str(user.rid))
            app.logger.info('[AUTH] [LOGIN] [Succeess] User:<%s>, role: <%s>', current_user.login, current_user.rid)
            return resp
        else:
            flash('Login or password incorrect')
            app.logger.warning('[AUTH] [LOGIN] [Failed] User:<%s> Password:<%s>', ulogin, upassword)
            return redirect(url_for('login'))
    else:
        return render_template("login.html")


@app.route('/logout', methods=['POST','GET'])
@login_required
def logout():
    app.logger.info('[AUTH] [LOGOUT] [Succeess] User:<%s>', current_user.login)
    logout_user()
    resp = make_response(redirect(url_for('index')))
    resp.set_cookie('rid', "", 0)
    return resp


@app.route('/reg', methods=['POST','GET'])
def reg():
    if request.method == "POST":
        ulogin=request.form['login']
        upassword=request.form['password']
        if not(ulogin or upassword):
            flash('Please, fill fileds: login, password')
            return redirect('/reg')
        elif not(TS_User.query.filter_by(login=ulogin).first()) and ulogin and upassword:
            user = TS_User(login=ulogin, password=generate_password_hash(upassword), email=request.form['email'], rid=0, token="")
            try:
                db.session.add(user)
                db.session.commit()
                app.logger.info('[AUTH] [REG] [Succeess] User:<%s>', ulogin)
                return redirect('/login')
            except:
                app.logger.error('[AUTH] [REG] [Failed] User:<%s>. Error DB insert.', ulogin)
                flash('Error DB insert')
                return redirect('/reg')
        else:
            app.logger.warning('[AUTH] [REG] [Failed] Please, enter other login or not null login or not null password')
            flash('Please, enter other login or not null login or not null password')
            return redirect('/reg')
    else:
        return render_template("reg.html")


@app.after_request
def redirect_to_login(response):
    if response.status_code == 401:
        return redirect('/login')
    return response


@app.route('/mytask')
@login_required
def mytask():
    tasks = TS_Task.query.filter(TS_Task.uid1==current_user.id).order_by(TS_Task.date.desc()).all()
    return render_template('task_mylist.html', tasks=tasks, team=team)


@app.route('/taskcreate', methods=['POST'])
@login_required
def taskcreate():
    if request.method == "POST":
        if (len(request.form['title']) > 2 and len(request.form['title']) < 13 and len(request.form['description']) < 255 and type(int(request.form['nteam'])) == int):
            task = TS_Task(title=request.form['title'], description=request.form['description'], linkpic=request.form['linkpic'], uid1=current_user.id, nteam=int(request.form['nteam']))
            try:
                db.session.add(task)
                db.session.commit()
                app.logger.info('[FUNC] [/taskcreate] [Succeess] User:<%s> Title:<%s> Description:<%s>',current_user.login, task.title, task.description)
                data = {''}
                res = f_httpreq(request.form['linkpic'])
                app.logger.info('[FUNC] [/taskcreate] [Succeess] User:<%s> print: url: <%s> data: <%s> result: <%s>', current_user.login, request.form['linkpic'], data, res)
                return redirect(url_for('mytask'))
            except:
                app.logger.error('[FUNC] [/taskcreate] [Failed] User:<%s> Error DB insert',current_user.login)
                flash('Error DB insert')
                return redirect(url_for('mytask'))
        else:
            flash('Please, enter all rewuired data!')
            return redirect(url_for('mytask'))
    else:
        return redirect(url_for('mytask'))


@app.route('/task/<int:tid>')
@login_required
def task_detail(tid):
    task = TS_Task.query.filter(and_(TS_Task.uid1==current_user.id, TS_Task.tid==tid)).order_by(TS_Task.date.desc()).first()
    if task:
        rid = current_user.rid
        app.logger.info('[FUNC] [/task] [Succeess] User:<%s> Role:<%d> Read task: <%s> owner:<%s>', current_user.login, rid, task.tid, task.TS_User.login)
        return render_template("task_detail.html", task=task)
    else:
        return redirect(url_for('mytask'))


@app.route('/task/<int:tid>/edit', methods=['POST','GET'])
@login_required
def task_edit(tid):
    task = TS_Task.query.filter(and_(TS_Task.uid1==current_user.id, TS_Task.tid==tid)).order_by(TS_Task.date.desc()).first()
    if task:
        if request.method == "POST":
            if (len(request.form['title']) > 2 and len(request.form['title']) < 13 and len(request.form['description']) < 255 and type(int(request.form['nteam'])) == int):
                task.title = request.form['title']
                task.description = request.form['description']
                task.linkpic = request.form['linkpic']
                task.nteam=int(request.form['nteam'])
                try:
                    db.session.commit()
                    app.logger.info('[FUNC] [/task/edit] [Succeess] User:<%s> Edit task: <%s> owner:<%s>', current_user.login, task.tid, task.TS_User.login)
                    return redirect(url_for('mytask'))
                except:
                    app.logger.error('[FUNC] [/task/edit] [Failed] User:<%s> Edit task: <%s> owner:<%s>. Error DB insert/', current_user.login, task.tid, task.TS_User.login)
                    flash('Error DB insert')
                    return redirect('/task/' + str(tid) + '/edit')
            else:
                flash('Please, enter all rewuired data!')
                return redirect('/task/' + str(tid) + '/edit')
        else:
            return render_template("task_edit.html", task=task, team=team)
    else:
        app.logger.warning('[FUNC] [/task/edit] [Failed] User:<%s> Edit task: <%s> owner:<%s>', current_user.login, task.tid, task.TS_User.login)
        return redirect(url_for('mytask'))


@app.route('/task/<int:tid>/del')
@login_required
def task_del(tid):
    task = TS_Task.query.filter(and_(TS_Task.uid1==current_user.id, TS_Task.tid==tid)).order_by(TS_Task.date.desc()).first()
    if task:
        try:
            db.session.delete(task)
            db.session.commit()
            app.logger.info('[FUNC] [/task/del] [Succeess] User:<%s> Del task: <%s> owner:<%s>', current_user.login, task.tid, task.TS_User.login)
        except:
            app.logger.error('[FUNC] [/task/del] [Failed] User:<%s> Del task: <%s> owner:<%s>. Error DB delete!', current_user.login, task.tid, task.TS_User.login)
            return "Error DB delete!"
    else:
        app.logger.warning('[FUNC] [/task/del] [Failed] User:<%s> Del task: <%s> owner:<%s>. Task not found!', current_user.login, task.tid, task.TS_User.login)
    return redirect(url_for('mytask'))


@app.route('/adm')
@login_required
def adm():
    reg = 0
    rid = current_user.rid
    page = request.args.get(get_page_parameter(), type=int, default=1)
    if rid == 2:
        tasks = TS_Task.query.filter(TS_Task.status==False).order_by(TS_Task.date.desc()).paginate(page=page, per_page=10)
        pagination = Pagination(page=page, total=tasks.total, record_name='task')
        app.logger.info('[FUNC] [/adminpanel] [Succeess] User:<%s> Role:<%d>/<%d> Read tasks: <%d>', current_user.login, current_user.rid, rid, len(tasks.items))
        return render_template("admpanel.html", tasks=tasks, pagination=pagination, team=team)
    app.logger.warning('[FUNC] [/adminpanel] [Failed] User:<%s> Access is denied from rid <%s>', current_user.login, current_user.rid)
    return redirect(url_for('index'))


@app.route('/adm/<int:tid>/print')
@login_required
def adm_print(tid):
    task = TS_Task.query.filter(TS_Task.tid==tid).order_by(TS_Task.date.desc()).first()
    if task:
        #data = {'team_id': task.nteam, 'text': task.title}
        url = hostrr + f'?team_id={task.nteam}&text={task.title}'
        res = f_httpreq(url)
        if res:
            app.logger.info('[FUNC] [/adminpanel/print] [Succeess] User:<%s> print: url: <%s> data: <%s>', current_user.login, hostrr, url)
            task.status = True
            try:
                db.session.commit()
                app.logger.info('[FUNC] [/adminpanel/print] [Succeess] DB insert! User:<%s> print: url: <%s> data: <%s>', current_user.login, hostrr, url)
            except:
                app.logger.error('[FUNC] [/adminpanel/print] [Failed] Error DB insert/ User:<%s> print: url: <%s> data: <%s>', current_user.login, hostrr, url)
        else:
            app.logger.error('[FUNC] [/adminpanel/print] [Failed] User:<%s> print: url: <%s> data: <%s>', current_user.login, hostrr, url)
    return redirect(url_for('adm'))


@app.route('/admreg', methods=['POST'])
def admreg():
    if request.method == "POST":
        ulogin=request.form['login']
        upassword=request.form['password']
        if not(ulogin or upassword):
            flash('Please, fill fileds: login, password')
            return redirect(url_for('adm'))
        elif not(TS_User.query.filter_by(login=ulogin).first()) and ulogin and upassword:
            user = TS_User(login=ulogin, password=generate_password_hash(upassword), email=request.form['email'], rid=2, token="")
            try:
                db.session.add(user)
                db.session.commit()
                app.logger.info('[AUTH] [admreg] [Succeess] User:<%s> Role:<%d> registartion captain:<%s>',current_user.login, current_user.rid, ulogin)
                return redirect(url_for('adm'))
            except:
                app.logger.error('[AUTH] [admreg] [Failed] User:<%s>. Error DB insert.', ulogin)
                flash('Error DB insert')
                return redirect(url_for('adm'))
        else:
            app.logger.warning('[AUTH] [admreg] [Failed] Please, enter other login or not null login or not null password')
            flash('Please, enter other login or not null login or not null password')
            return redirect(url_for('adm'))
    else:
        redirect(url_for('index'))