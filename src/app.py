from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash
from sqlalchemy import inspect, text
from functools import wraps
from config import Config
from config import config
from database import engine, db_session
from database.models import Usuario, Cita
from datetime import datetime
from database.models import Usuario, Cita

from itsdangerous import URLSafeTimedSerializer
serializador = URLSafeTimedSerializer(Config.SECRET_KEY)
from flask_mail import Mail, Message


app = Flask(__name__)


app.config.from_object(Config)
correo = Mail(app)

@app.route('/')
def index():
    return redirect(url_for('login'))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('usuario_id'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        nombre_usuario = request.form['nombre_usuario']
        contraseña = request.form['contraseña']
        usuario = db_session.query(Usuario).filter_by(nombre_usuario=nombre_usuario).first()
        if not usuario:
            error = 'El usuario no se encuentra registrado.'
        elif not usuario.verificar_contraseña(contraseña):
            error = 'Contraseña incorrecta.'
        else:
            session['usuario_id'] = usuario.id_usuario
            # Redirige según el rol
            if hasattr(usuario, 'rol') and usuario.rol == 'admin':
                return redirect(url_for('admin_citas'))
            else:
                return redirect(url_for('home'))
    return render_template('auth/login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        nombre_usuario = request.form['nombre_usuario']
        contraseña = request.form['contraseña']
        telefono = request.form['telefono']

        # Validar longitud de la contraseña
        if len(contraseña) < 6 or len(contraseña) > 20:
            error = 'La contraseña debe tener entre 6 y 20 caracteres.'
            return render_template('auth/register.html', error=error)
        
        if db_session.query(Usuario).filter_by(email=email).first():
            error = 'El correo ya está registrado'
        elif db_session.query(Usuario).filter_by(nombre_usuario=nombre_usuario).first():
            error = 'El usuario ya existe'
        else:
            usuario = Usuario(email, nombre_usuario, contraseña, telefono)
            db_session.add(usuario)
            db_session.commit()
            return redirect(url_for('login'))
    return render_template('auth/register.html', error=error)

@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    error = None
    mensaje = None
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        usuario = db_session.query(Usuario).filter_by(email=email).first()
        if usuario:
            token = serializador.dumps(usuario.email, salt='reinicio-contraseña')
            url_reinicio = url_for('reset_password', token=token, _external=True)
            msg = Message("Reinicio de Contraseña",
                          sender=app.config['MAIL_USERNAME'],
                          recipients=[usuario.email])
            msg.body = f"Para reiniciar tu contraseña, visita el siguiente enlace:\n{url_reinicio}\nEste enlace expirará en 1 hora."
            correo.send(msg)
            mensaje = "Se ha enviado un enlace para reiniar tu contraseña a {email}".format(email=usuario.email)
        else:
            error = "Correo no encontrado."
    return render_template('auth/reset_password_request.html', error=error, mensaje=mensaje)

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    error = None
    mensaje = None
    try:
        email = serializador.loads(token, salt='reinicio-contraseña', max_age=3600)
    except Exception:
        error = "El enlace es inválido o ha expirado."
        return render_template('auth/reset_password.html', error=error)
    
    usuario = db_session.query(Usuario).filter_by(email=email).first()
    if not usuario:
        error = "Usuario no encontrado."
        return render_template('auth/reset_password.html', error=error)
    
    if request.method == 'POST':
        nueva_contraseña = request.form['nueva_contraseña']
        if len(nueva_contraseña) < 6 or len(nueva_contraseña) > 20:
            error = "La nueva contraseña debe tener entre 6 y 20 caracteres."
        else:
            usuario.contraseña_hash = generate_password_hash(nueva_contraseña)
            db_session.commit()
            mensaje = "Contraseña actualizada correctamente."
    return render_template('auth/reset_password.html', error=error, mensaje=mensaje)


@app.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return redirect(url_for('login'))

    usuario = db_session.query(Usuario).get(usuario_id)
    error = None
    mensaje = None

    if request.method == 'POST':
        fecha = request.form['fecha']
        hora = request.form['hora']
        servicio = request.form['servicio']

        try:
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
            nueva_cita = Cita(
                id_usuario=usuario.id_usuario,
                fecha=fecha_obj,
                hora=hora,
                servicio=servicio
            )
            db_session.add(nueva_cita)
            db_session.commit()
            mensaje = "Cita agendada correctamente."
        except Exception as e:
            error = f"Error al agendar la cita: {e}"

    citas_usuario = db_session.query(Cita).filter_by(id_usuario=usuario.id_usuario).all()
    return render_template('home.html', usuario=usuario, citas=citas_usuario, error=error, message=mensaje)

@app.route('/citas/editar/<int:id_cita>', methods=['GET', 'POST'])
@login_required
def editar_cita_usuario(id_cita):
    usuario_id = session.get('usuario_id')
    cita = db_session.query(Cita).get(id_cita)
    # Solo puede editar si la cita es suya
    if not cita or cita.id_usuario != usuario_id:
        return redirect(url_for('home'))

    if request.method == 'POST':
        cita.fecha = request.form['fecha']
        cita.hora = request.form['hora']
        cita.servicio = request.form['servicio']
        db_session.commit()
        return redirect(url_for('home'))

    return render_template('editar_cita_usuario.html', cita=cita)

@app.route('/citas/borrar/<int:id_cita>')
@login_required
def borrar_cita_usuario(id_cita):
    usuario_id = session.get('usuario_id')
    cita = db_session.query(Cita).get(id_cita)
    # Solo puede borrar si la cita es suya
    if cita and cita.id_usuario == usuario_id:
        db_session.delete(cita)
        db_session.commit()
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.pop('usuario_id', None)
    return redirect(url_for('login'))

@app.route('/admin/citas')
@login_required
def admin_citas():
    usuario_id = session.get('usuario_id')
    usuario = db_session.query(Usuario).get(usuario_id)
    if not usuario or usuario.rol != 'admin':
        return redirect(url_for('home'))  # Solo admin puede acceder

    citas = db_session.query(Cita).all()
    return render_template('admin_citas.html', citas=citas)

@app.route('/admin/hacer_admin/<int:id_usuario>')
@login_required
def hacer_admin(id_usuario):
    usuario_id = session.get('usuario_id')
    usuario_actual = db_session.query(Usuario).get(usuario_id)
    if not usuario_actual or usuario_actual.rol != 'admin':
        return "No autorizado", 403

    usuario = db_session.query(Usuario).get(id_usuario)
    if usuario and usuario.rol != 'admin':
        usuario.rol = 'admin'
        db_session.commit()
        return redirect(url_for('database'))
    else:
        return "Usuario no encontrado o ya es admin", 404
    

@app.route('/admin/quitar_admin/<int:id_usuario>')
@login_required
def quitar_admin(id_usuario):
    usuario_id = session.get('usuario_id')
    usuario_actual = db_session.query(Usuario).get(usuario_id)
    if not usuario_actual or usuario_actual.rol != 'admin':
        return "No autorizado", 403

    usuario = db_session.query(Usuario).get(id_usuario)
    if usuario and usuario.rol == 'admin':
        usuario.rol = 'usuario'
        db_session.commit()
        return redirect(url_for('database'))
    else:
        return "Usuario no encontrado o no es admin", 404
    

@app.route('/admin/citas/editar/<int:id_cita>', methods=['GET', 'POST'])
@login_required
def editar_cita_admin(id_cita):
    usuario_id = session.get('usuario_id')
    usuario = db_session.query(Usuario).get(usuario_id)
    if not usuario or usuario.rol != 'admin':
        return redirect(url_for('home'))

    cita = db_session.query(Cita).get(id_cita)
    if not cita:
        return redirect(url_for('admin_citas'))

    if request.method == 'POST':
        cita.fecha = request.form['fecha']
        cita.hora = request.form['hora']
        cita.servicio = request.form['servicio']
        cita.estado = request.form['estado']
        db_session.commit()
        return redirect(url_for('admin_citas'))

    return render_template('editar_cita_admin.html', cita=cita)

@app.route('/admin/citas/borrar/<int:id_cita>')
@login_required
def borrar_cita(id_cita):
    usuario_id = session.get('usuario_id')
    usuario = db_session.query(Usuario).get(usuario_id)
    if not usuario or usuario.rol != 'admin':
        return redirect(url_for('home'))

    cita = db_session.query(Cita).get(id_cita)
    if cita:
        db_session.delete(cita)
        db_session.commit()
    return redirect(url_for('admin_citas'))


@app.route('/admin/database')
@login_required
def database():
    usuario_id = session.get('usuario_id')
    usuario = db_session.query(Usuario).get(usuario_id)
    if not usuario or usuario.rol != 'admin':
        return redirect(url_for('home'))

    inspector = inspect(engine)
    tablas = inspector.get_table_names()
    datos = {}

    for tabla in tablas:
        result = db_session.execute(text(f'SELECT * FROM {tabla}'))
        columnas = result.keys()
        filas = [dict(zip(columnas, row)) for row in result.fetchall()]
        datos[tabla] = {'columnas': columnas, 'filas': filas}

    return render_template('admin_database.html', tablas=datos)


if __name__ == '__main__':
    app.config.from_object(config['desarrollador'])
    app.run()