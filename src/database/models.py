from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Time, Date, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from werkzeug.security import generate_password_hash, check_password_hash
from database import metadata

Base = declarative_base(metadata=metadata)

class Usuario(Base):
    __tablename__ = 'usuarios'
    
    id_usuario = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(100), unique=True, nullable=False)
    telefono = Column(String(20), nullable=True)
    nombre_usuario = Column(String(50), unique=True, nullable=False)
    contraseña_hash = Column(Text, nullable=False)
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    rol = Column(String(20), default='usuario')
    
    citas = relationship("Cita", back_populates="usuario", cascade="all, delete-orphan")

    def __init__(self, email, nombre_usuario, contraseña, telefono=None):
        self.email = email.lower()
        self.nombre_usuario = nombre_usuario
        self.contraseña_hash = generate_password_hash(contraseña)
        self.telefono = telefono

    def verificar_contraseña(self, contraseña):
        return check_password_hash(self.contraseña_hash, contraseña)
    
    def __repr__(self):
        return f'<Usuario {self.nombre_usuario}>'

class Cita(Base):
    __tablename__ = 'citas'
    
    id_cita = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'), nullable=False)
    fecha = Column(Date, nullable=False)
    hora = Column(String(20), nullable=False)
    servicio = Column(String(100), nullable=False)
    estado = Column(String(20), default='pendiente')
    
    usuario = relationship("Usuario", back_populates="citas")

    def __repr__(self):
        return f'<Cita {self.id_cita} - {self.servicio}>'