## Modulo personalizado de ODOO 17

Este módulo esta destinado a gestionar los erasmus del centro.
Está implementado para ser instalado en la versión 17 de Odoo.

## Gestión de cambios
Al hacer cambios en el módulo se pueden generar inconsistencias con el despliegue. 
Para evitar estas inconsistencias ejecutar los siguientes comandos tras la actualización:
```bash
docker restart odoo17
docker exec -it [Nombre_contenedor_odoo] bash
odoo -u gestion_erasmus -d [Nombre_BBDD] --stop-after-init
exit
docker restart [Nombre_contenedor_Odoo]
```

