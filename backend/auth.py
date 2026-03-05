"""
Módulo de RBAC (Controle de Acesso Baseado em Perfis) e Autenticação.
Controla quais documentos os usuários podem acessar e gerencia usuários persistentes.
"""

import json
import os
from typing import Dict, List, Optional


ROLES = {
    "admin": {
        "description": "Acesso total a todos os documentos e operações do sistema.",
        "can_upload": True,
        "can_delete": True,
        "departments": ["*"],
    },
    "hr": {
        "description": "Acesso a documentos de RH e públicos.",
        "can_upload": True,
        "can_delete": False,
        "departments": ["hr", "public"],
    },
    "engineering": {
        "description": "Acesso a documentos de engenharia e públicos.",
        "can_upload": True,
        "can_delete": False,
        "departments": ["engineering", "public"],
    },
    "finance": {
        "description": "Acesso a documentos financeiros e públicos.",
        "can_upload": True,
        "can_delete": False,
        "departments": ["finance", "public"],
    },
    "public": {
        "description": "Acesso apenas a documentos públicos.",
        "can_upload": False,
        "can_delete": False,
        "departments": ["public"],
    },
}


DEPARTMENTS = ["hr", "engineering", "finance", "public"]

USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")


def load_users() -> Dict:
    """Carrega usuários do arquivo JSON."""
    if not os.path.exists(USERS_FILE):

        initial_users = {
            "admin": {
                "username": "admin",
                "password": "admin",
                "role": "admin",
                "department": "public"
            }
        }
        save_users(initial_users)
        return initial_users
        
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_users(users: Dict):
    """Salva usuários no arquivo JSON."""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """Valida credenciais e retorna info do usuário (sem senha)."""
    users = load_users()
    user = users.get(username)
    if user and user["password"] == password:
        user_info = user.copy()
        user_info.pop("password", None)
        return user_info
    return None


def list_users() -> List[Dict]:
    """Lista todos os usuários cadastrados."""
    users = load_users()
    user_list = []
    for _, info in users.items():
        user_info = info.copy()
        user_info.pop("password", None)
        user_list.append(user_info)
    return user_list


def add_user(username: str, password: str, role: str, department: str) -> bool:
    """Adiciona um novo usuário ao sistema."""
    users = load_users()
    if username in users:
        return False
    
    if role not in ROLES:
        return False

    users[username] = {
        "username": username,
        "password": password,
        "role": role,
        "department": department
    }
    save_users(users)
    return True


def delete_user(username: str) -> bool:
    """Remove um usuário (protege o admin padrão)."""
    if username == "admin":
        return False
        
    users = load_users()
    if username not in users:
        return False
        
    del users[username]
    save_users(users)
    return True


def validate_department(department: str) -> str:
    """Valida se o departamento existe, caso contrário retorna 'public'."""
    if department in DEPARTMENTS:
        return department
    return "public"


def get_accessible_departments(user_role: str) -> List[str]:
    """Retorna lista de departamentos acessíveis por um perfil."""
    role_config = ROLES.get(user_role, ROLES["public"])
    if "*" in role_config["departments"]:
        return DEPARTMENTS
    return role_config["departments"]


def can_upload(user_role: str) -> bool:
    """Verifica permissão de upload."""
    role_config = ROLES.get(user_role, ROLES["public"])
    return role_config["can_upload"]


def can_delete(user_role: str) -> bool:
    """Verifica permissão de exclusão."""
    role_config = ROLES.get(user_role, ROLES["public"])
    return role_config["can_delete"]


def get_role_info(user_role: str) -> Dict:
    """Retorna metadados resumidos de um perfil."""
    role_config = ROLES.get(user_role, ROLES["public"])
    return {
        "role": user_role if user_role in ROLES else "public",
        "description": role_config["description"],
        "can_upload": role_config["can_upload"],
        "can_delete": role_config["can_delete"],
        "accessible_departments": get_accessible_departments(user_role),
    }
