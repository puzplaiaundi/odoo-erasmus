# Odoo Dev – Gestión de Prácticas (Erasmus)

Entorno de desarrollo Dockerizado para Odoo 17 con módulos personalizados.

---

## 📦 Requisitos

Antes de comenzar, asegúrate de tener instalado:

- Docker Desktop (con WSL2 activado en Windows)
- Git
- Git Bash o terminal compatible

Comprobar instalación:

```bash
docker --version
git --version
```


# 📥 Clonar el repositorio

Clonar incluyendo los submódulos
```bash
git clone --recurse-submodules https://github.com/puzplaiaundi/odoo-dev.git
cd odoo-dev
```

Si ya lo clonaste sin submódulos: 
```bash
git submodule update --init --recursive
```
# ⚙ Configuración inicial
## 1. Crear archivo de configuración real
Copia el archivo de ejemplo: 
    
```bash
cp config/odoo.conf.example config/odoo.conf
```
    
Editar *config/odoo.conf* y cambiar:
```bash
admin_passwd= CHANGE_ME
```
por una contraseña segura.

## 🐳 Construir y levantar el entorno
Primera vez:
```bash
docker compose -f docker-compose.dev.yml up --build -d
```
En ejecuciones posteriores:
```bash
docker compose -f docker-compose.dev.yml up -d
```
## 🌐 Acceso a Odoo
Abrir el navegador:
```html
http://localhost:8069
```
## 🗄 Crear base de datos
1. Pulsar **Create Database**
2. Introducir la *admin_passwd* definida en *odoo.conf*
3. Crear la base de datos

## Instalar módulo
1. Activar modo desarrollador
2. Ir a Apps
3. Pulsar "Actualizar lista de aplicaciones"
4. Buscar gestion_erasmus
5. Instalar



