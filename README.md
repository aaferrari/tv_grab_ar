tv\_grab\_ar.py descarga la [grilla televisiva de Cablevision](https://www.cablevisionfibertel.com.ar/clientes/programacion) y la convierte en un archivo XML que se puede usar en programas como [tvtime](http://tvtime.sourceforge.net/) o cualquiera que sea compatible con [XMLTV](https://en.wikipedia.org/wiki/XMLTV).

Versión actualizada del script de Mauro Meloni publicado [aquí](http://maurom.com/blog/2010/02/03/tvtime-xmltv-tv_grab_ar-py/) (véase el CHANGELOG para mas detalles).

## Instalación
1.  Descargar tv\_grab_ar.py
2.  Instalar la librería de Python lxml:

    ```apt-get install python-lxml```
3.  Ejecutar `./tv_grab_ar.py --configure` e indicar la zona y los canales para los cuales se desea obtener la información.
4.  Ejecutar:

    ```./tv_grab_ar.py --verbose --sleep 0 --output=programacion.xml```
    
    para obtener la programación y las descripciones de los programas. Este proceso puede tomar mas o menos tiempo dependiendo de los parámetros `--days`, `--sleep` y `--threads`, así como de los canales configurados.

Para mantener la grilla actualizada se puede colocar en el cron una entrada para ejecutar el script al menos una vez por semana.

Para tener un marco de referencia a continuación se muestra cuanto tiempo demora el script en descargar la programación de todos los canales según la cantidad de días elegidos (con `--sleep 0`):

* Un día: 43 minutos.
* Tres días (por defecto): 73 minutos.
* Una semana: 124 minutos
* Programación completa (16 o 17 días): 408 minutos

