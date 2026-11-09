# -*- coding: utf-8 -*-
"""
Modelos de permisos, roles y asignación de permisos a roles.
`User.role` sigue siendo un string; la tabla `roles` solo registra los
nombres de rol disponibles (incluidos los personalizados creados por el
SUPERADMIN), y `role_permissions` asigna permisos a cada nombre de rol.
"""
from datetime import datetime

from app import db


class Permission(db.Model):
    """Permiso granular del sistema (ej. create_contract, edit_decree)."""
    __tablename__ = 'permissions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    module = db.Column(db.String(50), nullable=True)

    def __repr__(self):
        return f"<Permission {self.name} ({self.module})>"


class Role(db.Model):
    """Nombre de rol disponible. No reemplaza a `User.role` (string)."""
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    is_base = db.Column(db.Integer, nullable=False, default=0)  # 1 = rol del sistema
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<Role {self.name}>"


class RolePermission(db.Model):
    """Asigna un permiso a un rol (por nombre de rol)."""
    __tablename__ = 'role_permissions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role_name = db.Column(db.String(50), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey('permissions.id'), nullable=False)

    permission = db.relationship('Permission', backref='role_permissions')

    __table_args__ = (
        db.UniqueConstraint('role_name', 'permission_id', name='uq_role_permission'),
    )

    def __repr__(self):
        return f"<RolePermission {self.role_name} -> {self.permission.name}>"