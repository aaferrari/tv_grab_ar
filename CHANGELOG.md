##2021.05.15-1

* Se agrego soporte multihilo para peticiones concurrentes.
* Se migro el código a Python 3 manteniendo retrocompatibilidad con Python 2.
* Agregado manejo de excepciones de socket en la función `retrieve_fichacontent`.
* Mejoras:
  * En comprobación de títulos recortados en `completar_titulo`.
  * En obtención del titulo del programa en `parse_program`.
  * Se crea la función `clean_programs` para remover elementos nulos o redundantes de la lista de programación antes de generar el XML.
  * En `retrieve_descriptions` se comprueba si el titulo de un programa en la cache coincide con el de la ficha que se esta procesando.
* Dentro de `retrieve_channels` se finaliza el programa si no se detectan canales (por ejemplo, cuando el sitio esta caído o modificado) para que no se genere un XML vacío.
* Agregados los siguientes parámetros:
  * `--threads`: Cantidad de hilos que se usaran para realizar peticiones concurrentes.
  * `--sleep`: Intervalo en segundos para esperar entre peticiones dentro de cada hilo.

## 2015.03.02-1
Fix sutil al problema de encoding/decoding de títulos.

## 2014.02.22-1
Adaptación del código a PEP-8.

## 2014.10.22-1
Re-incorporación del cache y descarga de descripciones.

## 2014.10.16-1
Fix sutil por cambio en el diseño del sitio web.

## 2014.06.21-2
Salida de temporada y episodio en formato xmltv_ns.

## 2014.06.21-1
Fix sutil para descargar la programación nocturna.

## 2014.06.20-1
Fixes por separación en horas al obtener la grilla de datos.

## 2013.11.17-1
Fix para cuando es incorrecta la hora de un programa.

## 2013.11.10-1
Fix para cuando no puede obtenerse el numero de episodio.

## 2013.10.19-1rc
Selección correcta de la zona previo a la descarga.

## 2013.10.08-4rc
Conversión desde optparse a argparse.

## 2013.10.08-3rc
Implementación de parámetros `days` y `offset`.

## 2013.10.08-2rc
Fixes para que valide contra xmltv.dtd.

## 2013.10.08-1rc
Nuevo método de descarga de grilla y fichas.

## 2013.10.07-1rc
Reescritura completa por cambio en el sitio web.

## 2012.12.04-1
Fix sutil por cambio en el diseño del sitio web.

## 2012.05.02-1
Tratamiento de excepción ante errores de HTTP y DNS.

## 2012.04.04-1
Tratamiento de excepción ante `fichaId` invalida.

## 2012.03.24-1
Solo se guarda el cache al fin del proceso (faster!).

## 2011.12.25-1
Los mensajes de información van ahora a stderr.

## 2011.12.22-1
(Bug)fixes en la selección de zona y canales.

## 2011.09.16-1
Nueva recuperación de canales por rediseño de la web.

## 2011.09.15-1
Salida de fecha y hora utilizando huso horario UTC.

## 2011.09.14-1
Implementados switches `capabilities` y `description`.

## 2011.06.06-1
Backup del archivo de fichas en caso de corrupción

## 2011.05.30-1
Fix error de codificación al mostrar la lista de zonas

## 2011.04.27-1
Fix para despliegue de nombres de canal (gracias a Donato).

## 2011.03.11-1
Adición de cambio de zona (gracias a Mariano Cosentino).

## 2010.11.19-1
Modificación para que lea el genero de los programas.

## 2010.10.16-1
Posibilidad de obtener grilla de la semana posterior.

## 2010.09.13-1
Crea directorios de configuración si no existen.

## 2010.09.11-1
Adición de posibilidad de cambio de zona.

## 2010.09.06-1
Fix para `fichaId` vaciá.

## 2010.08.24-1
Nuevas rutinas debido al rediseño del sitio web.

## 2010.08.19-1
Pretty-Print XML.

## 2010.08.18-1
Adición de esperas para evitar saturar al servidor.

## 2010.08.17-1
Conversión desde beautifulsoup a lxml (faster!).

## 2010.07.19-1
Fix para manejar los valores de canales en el menú.

## 2010.05.19-1
Crear cookie de zona en vez de obtenerla del sitio.

## 2010.04.27-1
Cambio de url para `retrieve_descriptions`.

## 2010.04.25-1
Cambio de url para `retrieve_programs`.

## 2010.04.06-1
Manejo de excepción al obtener las descripciones.

## 2010.03.31-2
Manejo de excepción al obtener la programación semanal.

## 2010.03.31-1
Multicanal es ahora Cablevision.

## 2009.09.21-1
Fix para Multicanal, que tiene mal el nro de TCM.

## 2009.09.17-3
Despliegue de genero como subtitulo.

## 2009.09.17-2
Fix para programas emitidos en días sucesivos.

## 2009.09.17-1
Corrección de stationlist.xml.

## 2009.09.16-6
Xmltv Writer ad hoc.

## 2009.09.16-5
Descarga de canales ordenados por id.

## 2009.09.16-4
Cache de fichas.

## 2009.09.16-3
Fixes a temas de encoding.

## 2009.09.16-2
Recuperación de descripciones.

## 2009.09.16-1
Versión inicial.
