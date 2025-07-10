from database import db_session
from database.models import Usuario

# Cambia esto por el nombre de usuario que quieres hacer admin
nombre_usuario = 'migi'

usuario = db_session.query(Usuario).filter_by(nombre_usuario=nombre_usuario).first()
if usuario:
    usuario.rol = 'admin'
    db_session.commit()
    print(f"El usuario {nombre_usuario} ahora es admin.")
else:
    print("Usuario no encontrado.")