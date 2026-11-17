"""Local accounts, revocable sessions and role checks."""
from contextlib import closing
import hashlib
import re
import secrets
import sqlite3
import time

from flask import abort, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

ROLES = {'admin': 'Administrador', 'client': 'Cliente'}
SESSION_SECONDS = 8 * 60 * 60


class Accounts:
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connection() as db, db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL, password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('admin','client')),
                    active INTEGER NOT NULL DEFAULT 1);
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL,
                    expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS attempts (ip TEXT NOT NULL, at REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS attempts_ip ON attempts(ip, at);
            ''')
            db.execute('INSERT OR IGNORE INTO settings VALUES (?,?)', ('secret', secrets.token_hex(32)))
            self.secret = db.execute("SELECT value FROM settings WHERE key='secret'").fetchone()[0]
        self.dummy_hash = generate_password_hash(secrets.token_hex(24))

    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return closing(db)

    @staticmethod
    def validate(username, name, password, role):
        username = username.strip().lower()
        name = name.strip()
        if not re.fullmatch(r'[a-z0-9_.-]{3,40}', username):
            raise ValueError('El usuario debe tener entre 3 y 40 letras sin tildes, números, puntos, guiones o guiones bajos.')
        if not 1 <= len(name) <= 80:
            raise ValueError('El nombre debe tener entre 1 y 80 caracteres.')
        if not 12 <= len(password) <= 128:
            raise ValueError('La contraseña debe tener entre 12 y 128 caracteres.')
        if role not in ROLES:
            raise ValueError('Rol inválido.')
        return username, name

    def create_user(self, username, name, password, role='client', first=False):
        username, name = self.validate(username, name, password, role)
        password_hash = generate_password_hash(password)
        with self.connection() as db, db:
            db.execute('BEGIN IMMEDIATE')
            if first and db.execute('SELECT 1 FROM users LIMIT 1').fetchone():
                raise ValueError('La cuenta inicial ya fue creada.')
            try:
                cur = db.execute('INSERT INTO users(username,name,password_hash,role) VALUES (?,?,?,?)',
                                 (username, name, password_hash, role))
            except sqlite3.IntegrityError:
                raise ValueError('Ese nombre de usuario ya existe.') from None
            return cur.lastrowid

    def has_users(self):
        with self.connection() as db:
            return bool(db.execute('SELECT 1 FROM users LIMIT 1').fetchone())

    def users(self):
        with self.connection() as db:
            return db.execute('SELECT id,username,name,role,active FROM users ORDER BY username').fetchall()

    def authenticate(self, username, password, ip):
        now = time.time()
        with self.connection() as db, db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM attempts WHERE at < ?', (now - 900,))
            if db.execute('SELECT COUNT(*) FROM attempts WHERE ip=?', (ip,)).fetchone()[0] >= 10:
                return None, 429
            db.execute('INSERT INTO attempts VALUES (?,?)', (ip, now))
            user = db.execute('SELECT * FROM users WHERE username=?', (username.strip().lower(),)).fetchone()
        valid = check_password_hash(user['password_hash'] if user else self.dummy_hash, password)
        if not user or not valid or not user['active']:
            return None, 401
        with self.connection() as db, db:
            db.execute('DELETE FROM attempts WHERE ip=?', (ip,))
        return user, 200

    def new_session(self, user_id):
        token = secrets.token_urlsafe(32)
        with self.connection() as db, db:
            db.execute('DELETE FROM sessions WHERE expires < ?', (time.time(),))
            db.execute('INSERT INTO sessions VALUES (?,?,?)',
                       (self.token_hash(token), user_id, time.time() + SESSION_SECONDS))
        return token

    @staticmethod
    def token_hash(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def current_user(self, token):
        if not token:
            return None
        with self.connection() as db:
            return db.execute('''SELECT u.id,u.username,u.name,u.role FROM users u
                JOIN sessions s ON s.user_id=u.id
                WHERE s.token_hash=? AND s.expires>? AND u.active=1''',
                (self.token_hash(token), time.time())).fetchone()

    def logout(self, token):
        with self.connection() as db, db:
            db.execute('DELETE FROM sessions WHERE token_hash=?', (self.token_hash(token or ''),))

    def update_user(self, user_id, role, active, password=None):
        if role not in ROLES:
            raise ValueError('Rol inválido.')
        password_hash = None
        if password:
            self.validate('valid', 'valid', password, role)
            password_hash = generate_password_hash(password)
        with self.connection() as db, db:
            db.execute('BEGIN IMMEDIATE')
            user = db.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
            if not user:
                raise ValueError('Cuenta no encontrada.')
            if user['role'] == 'admin' and user['active'] and (role != 'admin' or not active):
                count = db.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND active=1").fetchone()[0]
                if count <= 1:
                    raise ValueError('Debe quedar al menos un administrador activo.')
            db.execute('UPDATE users SET role=?,active=? WHERE id=?', (role, int(active), user_id))
            if password_hash:
                db.execute('UPDATE users SET password_hash=? WHERE id=?', (password_hash, user_id))
            if password_hash or role != user['role'] or int(active) != user['active']:
                db.execute('DELETE FROM sessions WHERE user_id=?', (user_id,))

    def change_password(self, user_id, old, new):
        self.validate('valid', 'valid', new, 'client')
        new_hash = generate_password_hash(new)
        with self.connection() as db, db:
            db.execute('BEGIN IMMEDIATE')
            user = db.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
            if not user or not check_password_hash(user['password_hash'], old):
                raise ValueError('La contraseña actual no es correcta.')
            db.execute('UPDATE users SET password_hash=? WHERE id=?', (new_hash, user_id))
            db.execute('DELETE FROM sessions WHERE user_id=?', (user_id,))


def init_auth(app, path):
    accounts = Accounts(path)
    app.extensions['accounts'] = accounts
    app.config.update(SECRET_KEY=accounts.secret, SESSION_COOKIE_HTTPONLY=True,
                      SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_NAME='pluvia_session')

    def csrf_token():
        if 'csrf' not in session:
            session['csrf'] = secrets.token_urlsafe(32)
        return session['csrf']

    app.jinja_env.globals.update(csrf_token=csrf_token, roles=ROLES)

    @app.before_request
    def protect():
        g.user = accounts.current_user(session.get('sid'))
        public = request.endpoint in ('login', 'static')
        if not public and not g.user:
            if request.path.startswith('/api/'):
                return jsonify(error='Inicia sesión para continuar.'), 401
            return redirect(url_for('login'))
        if (request.path.startswith('/admin') or request.path.startswith('/api/admin')) and (not g.user or g.user['role'] != 'admin'):
            abort(403)
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token', '')
            if not session.get('csrf') or not secrets.compare_digest(token, session['csrf']):
                if request.path.startswith('/api/'):
                    return jsonify(error='La sesión del formulario venció. Recarga la página.'), 403
                abort(403)

    @app.after_request
    def private_response(response):
        if request.endpoint != 'static':
            response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    @app.errorhandler(403)
    def forbidden(error):
        if request.path.startswith('/api/'):
            return jsonify(error='No tienes permiso para esta operación.'), 403
        return render_template('access_error.html'), 403

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if g.user:
            return redirect(url_for('index'))
        error, status = None, 200
        if request.method == 'POST':
            username = request.form.get('username', '')[:40]
            password = request.form.get('password', '')
            user, status = accounts.authenticate(username, password[:129], request.remote_addr or 'local')
            if user:
                session.clear()
                session['sid'] = accounts.new_session(user['id'])
                csrf_token()
                return redirect(url_for('index'))
            error = ('Demasiados intentos. Espera 15 minutos antes de volver a intentar.'
                     if status == 429 else 'Usuario o contraseña incorrectos, o cuenta desactivada.')
        return render_template('login.html', error=error, initialized=accounts.has_users()), status

    @app.post('/logout')
    def logout():
        accounts.logout(session.get('sid'))
        session.clear()
        return redirect(url_for('login'))

    @app.route('/account', methods=['GET', 'POST'])
    def account():
        error = None
        if request.method == 'POST':
            try:
                if request.form.get('password') != request.form.get('confirmation'):
                    raise ValueError('Las contraseñas nuevas no coinciden.')
                accounts.change_password(g.user['id'], request.form.get('current_password', ''), request.form.get('password', ''))
                session.clear()
                return redirect(url_for('login'))
            except ValueError as exc:
                error = str(exc)
        return render_template('account.html', error=error), 400 if error else 200

    @app.route('/admin/users', methods=['GET', 'POST'])
    def admin_users():
        error = None
        if request.method == 'POST':
            try:
                accounts.create_user(request.form.get('username', ''), request.form.get('name', ''),
                                     request.form.get('password', ''), request.form.get('role', ''))
                return redirect(url_for('admin_users'))
            except ValueError as exc:
                error = str(exc)
        return render_template('users.html', users=accounts.users(), error=error), 400 if error else 200

    @app.post('/admin/users/<int:user_id>')
    def edit_user(user_id):
        try:
            accounts.update_user(user_id, request.form.get('role', ''), request.form.get('active') == '1',
                                 request.form.get('password') or None)
        except ValueError as exc:
            return render_template('users.html', users=accounts.users(), error=str(exc)), 400
        return redirect(url_for('admin_users'))

    return accounts
