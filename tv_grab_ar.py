#!/usr/bin/python
#
# tv_grab_ar.py
#
# Copyright 2009-2014, Mauro A. Meloni <maurom1982@yahoo.com.ar>
# http://maurom.com/blog/2010/02/03/tvtime-xmltv-tv_grab_ar-py
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
# Version history:
#
# 2015.03.02-1     Fix sutil al problema de encoding/decoding de titulos
# 2014.02.22-1     Adaptacion del codigo a PEP-8
# 2014.10.22-1     Re-incorporacion del cache y descarga de descripciones
# 2014.10.16-1     Fix sutil por cambio en el disenio del sitio web
# 2014.06.21-2     Salida de temporada y episodio en formato xmltv_ns
# 2014.06.21-1     Fix sutil para descargar la programacion nocturna
# 2014.06.20-1     Fixes por separacion en horas al obtener la grilla de datos
# 2013.11.17-1     Fix para cuando es incorrecta la hora de un programa
# 2013.11.10-1     Fix para cuando no puede obtenerse el nro de episodio
# 2013.10.19-1rc   Seleccion correcta de la zona previo a la descarga
# 2013.10.08-4rc   Conversion desde optparse a argparse
# 2013.10.08-3rc   Implementacion de parametros days y offset
# 2013.10.08-2rc   Fixes para que valide contra xmltv.dtd
# 2013.10.08-1rc   Nuevo metodo de descarga de grilla y fichas
# 2013.10.07-1rc   Reescritura completa por cambio en el sitio web
# 2012.12.04-1     Fix sutil por cambio en el disenio del sitio web
# 2012.05.02-1     Tratamiento de excepcion ante errores de HTTP y DNS
# 2012.04.04-1     Tratamiento de excepcion ante fichaId invalida
# 2012.03.24-1     Solo se guarda el cache al fin del proceso (faster!)
# 2011.12.25-1     Los mensajes de informacion van ahora a stderr
# 2011.12.22-1     (Bug)fixes en la seleccion de zona y canales
# 2011.09.16-1     Nueva recuperacion de canales por redisenio de la web
# 2011.09.15-1     Salida de fecha y hora utilizando huso horario UTC
# 2011.09.14-1     Implementados switches capabilities y description
# 2011.06.06-1     Backup del archivo de fichas en caso de corrupcion
# 2011.05.30-1     Fix error de codificacion al mostrar la lista de zonas
# 2011.04.27-1     Fix p/despliegue de nombres de canal (gracias a Donato)
# 2011.03.11-1     Adicion de cambio de zona (gracias a Mariano Cosentino)
# 2010.11.19-1     Modificacion para que lea el genero de los programas
# 2010.10.16-1     Posibilidad de obtener grilla de la semana posterior
# 2010.09.13-1     Crea directorios de configuracion si no existen
# 2010.09.11-1     Adicion de posibilidad de cambio de zona
# 2010.09.06-1     Fix para fichaId vacia
# 2010.08.24-1     Nuevas rutinas debido al redisenio del sitio web
# 2010.08.19-1     Pretty-Print XML
# 2010.08.18-1     Adicion de esperas para evitar saturar al servidor
# 2010.08.17-1     Conversion desde beautifulsoup a lxml (faster!)
# 2010.07.19-1     Fix para manejar los valores de canales en el menu
# 2010.05.19-1     Crear cookie de zona en vez de obtenerla del sitio
# 2010.04.27-1     Cambio de url para retrieve_descriptions
# 2010.04.25-1     Cambio de url para retrieve_programs
# 2010.04.06-1     Manejo de excepcion al obtener las descripciones
# 2010.03.31-2     Manejo de excepcion al obtener la programacion semanal
# 2010.03.31-1     Multicanal es ahora Cablevision
# 2009.09.21-1     Fix para multicanal, que tiene mal el nro de TCM
# 2009.09.17-3     Despliegue de genero como subtitulo
#            2     Fix para programas emitidos en dias sucesivos
# 2009.09.17-1     Correccion de stationlist.xml
# 2009.09.16-6     Xmltv Writer ad hoc
#            5     Descarga de canales ordenados por id
#            4     Cache de fichas
#            3     Fixes a temas de encoding
#            2     Recuperacion de descripciones
# 2009.09.16-1     Version inicial
#

from __future__ import print_function
import argparse
import codecs
from datetime import datetime, date, time, timedelta, tzinfo
import json
from lxml import etree, html
from os import mkdir, rename
from os.path import basename, dirname, expanduser, join, isdir, isfile, splitext
import re
from shutil import copy
import sys
from time import sleep
from multiprocessing.pool import ThreadPool
from functools import partial, cmp_to_key
from socket import error as socket_error
from threading import Lock
# Codigo necesario para mantener la retrocompatibilidad con Python 2
if sys.version_info.major == 2:
    import cPickle
    from StringIO import StringIO
    from urllib import quote_plus
    import urllib2
elif sys.version_info.major == 3:
    from urllib import request as urllib2
    import pickle as cPickle
    from io import StringIO
    from urllib.parse import quote_plus
    from imp import reload
    xrange = range


VERSION = '2015.03.02-1'
LANG = u'es'
DATETIME_FMT = '%Y%m%d%H%M %Z'
TVTIME_CONFIG_DIR = expanduser('~/.tvtime')
XMLTV_CONFIG_DIR = expanduser('~/.xmltv')
SLEEP_TIME = 1.3
THREADS = 20

s_print_lock = Lock()

def s_print(*a, **b):
    """Funcion print para multihilo"""
    with s_print_lock:
        print(*a, **b)

def parse_style(styledef):
    """Obtener una serie de pares (clave, valor) a partir de una linea de
    estilos CSS.
    """
    style = {}
    items = styledef.split(';')
    map(''.strip, items)
    for item in items:
        try:
            (tag, value) = item.split(':')
        except ValueError:
            continue
        style[tag.strip()] = value.strip()
    return style


def remove_letters(data):
    """Eliminar las letras de un texto, dejando solo numeros y guion."""
    return re.sub(r'[^-0-9]', '', data)


def sec_to_hour(seconds):
    """Retornar una cantidad de segundos en formato 00:00."""
    return '%02d:%02d' % (seconds / 3600, (seconds / 60) % 60)


def fix_encoding(text):
    """Tratar de corregir texto mal codificado."""
    try:
        return text.encode('latin1').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


def completar_titulo(titulo_trunco, titulo_completo):
    """Completar una cadena trunca a partir de otra en mayusculas."""
    correcto = titulo_trunco[:-3]
    if titulo_trunco.endswith('...') and \
       len(correcto) < len(titulo_completo) and \
       titulo_completo.lower().startswith(correcto.lower()) == True:
        return correcto + titulo_completo[len(correcto):].lower()
    return titulo_trunco


class GMT (tzinfo):
    """Zona horaria."""

    def __init__(self, offset):
        self.__offset = timedelta(hours=offset)
        if offset < 0:
            sign = '-'
        else:
            sign = '+'
        self.__name = sign + '%02d' % abs(offset) + '00'

    def utcoffset(self, dt):
        """Retornar el offset con respecto a UTC."""
        return self.__offset

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        """Retornar el nombre de la zona horaria."""
        return self.__name


class Writer:
    """Generador de XML."""

    def __init__(self, datestr, encoding, source_info_url, source_info_name, generator_info_name, generator_info_url):
        self.encoding = encoding
        self.datestr = datestr
        self.source_info_url = source_info_url
        self.source_info_name = source_info_name
        self.generator_info_name = generator_info_name
        self.generator_info_url = generator_info_url
        self.channels = []
        self.programs = []

    def addChannel(self, d):
        """Agregar un canal al XML."""
        self.channels.append(d)

    def addProgramme(self, d):
        """Agregar un programa al XML."""
        self.programs.append(d)

    def xml_start(self):
        """Retornar una plantilla de fichero XML."""
        template = '''<?xml version="1.0" encoding="%s"?>
<!DOCTYPE tv SYSTEM "xmltv.dtd">

<tv date="%s" generator-info-name="%s" generator-info-url="%s" source-info-name="%s" source-info-url="%s">
</tv>
'''
        return template % (
            self.encoding,
            self.datestr,
            self.generator_info_name,
            self.generator_info_url,
            self.source_info_name,
            self.source_info_url,
        )

    def channel_to_xml(self, d):
        """Retornar un ElementTree a partir de un diccionario que representa
        un canal."""
        elem = etree.Element('channel', { 'id': u'xmltv.' + unicode(d['id']) } )
        for (text, lang) in d['display-name']:
            etree.SubElement(elem, 'display-name', { 'lang': lang } ).text = unicode(text)
        if 'icon' in d:
            for item in d['icon']:
                etree.SubElement(elem, 'icon', { 'src': item } )
        return elem

    def program_to_xml(self, d):
        """Retornar un ElementTree a partir de un diccionario que representa
        un programa.
        """
        attrs = {
            'channel': u'xmltv.' + unicode(d['channel']),
            'start': d['start'],
            'stop': d['stop'],
        }
        credits = None
        elem = etree.Element('programme', attrs)
        if 'title' in d:
            itemtext, itemlang = d['title']
            etree.SubElement(elem, 'title', { 'lang': itemlang } ).text = itemtext
        if 'sub-title' in d:
            itemtext, itemlang = d['sub-title']
            etree.SubElement(elem, 'sub-title', { 'lang': itemlang } ).text = itemtext
        if 'desc' in d:
            for (itemtext, itemlang) in d['desc']:
                etree.SubElement(elem, 'desc', { 'lang': itemlang } ).text = itemtext
        if 'directors' in d:
            if credits is None:
                credits = etree.SubElement(elem, 'credits')
            for name in d['directors']:
                etree.SubElement(credits, 'director').text = name
        if 'actors' in d:
            if credits is None:
                credits = etree.SubElement(elem, 'credits')
            for name in d['actors']:
                etree.SubElement(credits, 'actor').text = name
        if 'date' in d:
            etree.SubElement(elem, 'date').text = d['date']
        if 'category' in d:
            for (itemtext, itemlang) in d['category']:
                etree.SubElement(elem, 'category', { 'lang': itemlang } ).text = itemtext
        if 'length' in d:
            itemtext, units = d['length']
            etree.SubElement(elem, 'length', { 'units': units } ).text = itemtext
        if 'icon' in d:
            for item in d['icon']:
                etree.SubElement(elem, 'icon').set('src', item)
        if 'url' in d:
            etree.SubElement(elem, 'url').text = d['url']
        if 'country' in d:
            itemtext, itemlang = d['country']
            etree.SubElement(elem, 'country', { 'lang': itemlang } ).text = itemtext
        if 'episode-num' in d:
            itemtext, system = d['episode-num']
            etree.SubElement(elem, 'episode-num', { 'system': system } ).text = itemtext
        if 'rating' in d:
            itemcode, itemtext, icon = d['rating']
            relem = etree.SubElement(elem, 'rating', { 'system': 'MPAA' })
            etree.SubElement(relem, 'value').text = itemcode
            etree.SubElement(relem, 'icon', { 'src': icon })
        return elem

    def indent(self, elem, level=0):
        """Agregar indentacion a un ElementTree y todos sus nodos hijos."""
        # By Filip Salomonsso
        # http://infix.se/2007/02/06/gentlemen-indent-your-xml
        i = "\n" + level * "\t"
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "\t"
            for e in elem:
                self.indent(e, level+1)
                if not e.tail or not e.tail.strip():
                    e.tail = i + "\t"
            if not e.tail or not e.tail.strip():
                e.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    def build_tree(self):
        """Construir a partir de la plantilla, los canales y los programas,
        un arbol ElementTree ya identado.
        """
        tree = etree.parse(StringIO(self.xml_start()))
        root = tree.getroot()
        for d in self.channels:
            root.append(self.channel_to_xml(d))
        for d in self.programs:
            root.append(self.program_to_xml(d))
        self.indent(tree.getroot())
        return tree

    def writetofile(self, filename):
        """Escribir el arbol XML a un archivo."""
        tree = self.build_tree()
        tree.write(
            filename,
            encoding='utf-8',
            xml_declaration=True,
        )

    def tostring(self):
        """Retornar el arbol XML como una cadena."""
        tree = self.build_tree()
        data = etree.tostring(
            tree,
            encoding='utf-8',
            xml_declaration=True,
        )
        return data


class XmltvChannel:
    """Canal de television."""

    def __init__(self, id_, number, name):
        self.id = int(id_)
        self.number = int(number)
        self.name = name
        self.icon = None
        self.url = None
        self.enabled = True
        self.description = ''
        self.num_programs = 0

    def get_dict(self):
        """Retornar un diccionario a partir de la informacion del canal."""
        d = {}
        d['id'] = int(self.id)
        d['display-name'] = [
            (self.name, LANG),
            (self.number, LANG),
        ]
        if self.icon: d['icon'] = [self.icon]
        if self.url: d['url'] = self.url
        return d

    def __str__(self):
        return '%3d - %s (id %d)' % (self.number, self.name.encode('utf-8'), self.id)


class XmltvProgram:
    """Programa de television."""

    def __init__(self):
        self.channel = None
        self.start = None
        self.stop = None
        self.title = ''
        self.description = ''
        self.ficha = None
        self.duration = None
        self.starthour = None
        self.data = None

    def full_title(self):
        """Retornar el titulo completo del programa de television."""
        if self.sub_title():
            return self.title + ' - ' + self.sub_title()
        return self.title

    def sub_title(self):
        """Retornar el subtitulo del programa de television."""
        fragments = []
        if not self.data:
            return ''
        if 'titleSeason' in self.data:
            fragments.append(self.data['titleSeason'])
        if 'titleChapter' in self.data:
            fragments.append(self.data['titleChapter'])
        return ' - '.join(fragments)

    def xmltv_ns_episode_number(self):
        """Retornar el numero de episodio (si existiera) en formato XMLTV NS."""
        try:
            numseason = int(remove_letters(self.data['titleSeason'].replace('-', '')))
            numseason = str(max(0, numseason - 1))
        except (KeyError, ValueError):
            numseason = ''
        try:
            numepisode = int(remove_letters(self.data['titleChapter'].replace('-', '')))
            numepisode = str(max(0, numepisode - 1))
        except (KeyError, ValueError):
            numepisode = ''
        if numseason == '' and numepisode == '':
            return None
        return '%s.%s.' % (numseason, numepisode)

    def get_dict(self):
        """Retornar un diccionario a partir de la informacion del programa."""
        d = {}
        d['channel'] = int(self.channel)
        d['title'] = (self.title, LANG)
        if self.description:
            d['desc'] = [(self.description, LANG)]
        d['start'] = self.start.strftime(DATETIME_FMT)
        d['stop'] = self.stop.strftime(DATETIME_FMT)
        if self.data:
            for key in ('G\xc3\xa9nero', u'G\xe9nero'):
                if key not in self.data: continue
                cats = []
                for cat in self.data[key].split(','):
                    cats.append((cat.strip(), LANG))
                d['category'] = cats
            for key in ('Pa&iacute;s', u'Pa\xeds'):
                if key not in self.data: continue
                d['country'] = (self.data[key], LANG)
            for key in ('A&ntilde;o', u'A\xf1o'):
                if key not in self.data: continue
                d['date'] = self.data[key]
            for key in ('Actor', 'Actores'):
                if key not in self.data: continue
                d['actors'] = self.data[key]
            for key in ('Director', 'Directores'):
                if key not in self.data: continue
                d['directors'] = self.data[key]
            if 'titleChapter' in self.data:
                number = remove_letters(self.data['titleChapter'].replace('-', ''))
                if number != '':
                    d['episode-num'] = (number, 'onscreen')
            xmltv_ns = self.xmltv_ns_episode_number()
            if xmltv_ns is not None:
                d['episode-num'] = (xmltv_ns, 'xmltv_ns')
            key = 'chapaParentalProgramFicha'
            if key in self.data:
                d['rating'] = self.data[key]
            key = 'lb_gallery'
            if key in self.data:
                d['icon'] = self.data[key]
            key = 'url'
            if key in self.data:
                d['url'] = self.data[key]
            # key = 'duracionGrilla'
            # if key in self.data and self.data[key].find('min') != -1:
            #     d['length'] = (remove_letters(self.data[key]), 'minutes')
            if self.sub_title():
                d['sub-title'] = (self.sub_title(), LANG)
        return d

    def __str__(self):
        retval = ''
        if self.channel is not None:
            retval  = 'Channel: \t%s\n' % self.channel
        retval += 'Title: \t%s\n' % self.title.encode('utf-8')
        retval += 'Description: \t%s\n' % self.description
        if self.start is not None:
            retval += 'Start: \t%s\n' % self.start
        if self.stop is not None:
            retval += 'Stop: \t%s\n' % self.stop
        if self.duration is not None:
            retval += 'Duration: \t%s\n' % sec_to_hour(self.duration)
        if self.starthour is not None:
            retval += 'Start Hour: \t%s\n' % sec_to_hour(self.starthour)
        retval += 'Data:\n'
        if self.data:
            for item in self.data:
                retval += '\t%s: %s\n' % (item, self.data[item])
        return retval


class TvGrabAr:

    TIME_CONST = 30.0 / 102 * 60

    def __init__(self, provider = 'CABLEVISIONFIBERTEL'):
        self.options = None
        self.base_url = None
        self.base_domain = None
        if provider == 'CABLEVISIONFIBERTEL':
            self.base_domain = 'buscador.cablevisionfibertel.com.ar'
            self.base_url = 'https://' + self.base_domain
        self.opener = urllib2.build_opener(urllib2.ProxyHandler())
        self.input_timezone  = GMT(-3)   # zona horaria de la grilla
        self.output_timezone = GMT(0)    # salida en UTC por defecto
        self.fichas = {}
        self.codigo_zona = None
        self.nombre_zona = None
        self.digClasId = None   # requerido para el seteo de zona
        self.digHd = None       # requerido para el seteo de zona

    def description(self):
        """Retornar la descripcion del script."""
        print('Argentina (%s)' % self.base_domain)

    def capabilities(self):
        """Retornar las capacidades del script."""
        print('baseline')
        print('manualconfig')
        print('cache')

    def get_config_zona(self):
        """Tomar la zona indicada desde linea de comandos, o la existente en
        el archivo de configuracion, o bien establecer la zona por defecto.
        """
        # if not isdir(dirname(self.options.config_file)):
        #     mkdir(dirname(self.options.config_file))
        # si fue establecida por parametro
        if self.options.codigo_zona:
            self.codigo_zona = self.options.codigo_zona
            self.nombre_zona = 'USER SELECTED LOCATION'
            return
        # si esta en el archivo de configuracion
        if isfile(self.options.config_file):
            for line in open(self.options.config_file):
                datum, id_, name = line.strip().split(' ', 2)
                if datum == 'location':
                    if int(id_) != 0:
                        self.codigo_zona = int(id_)
                        self.nombre_zona = name
                        return
        # en cualquier otro caso
        self.codigo_zona = None
        self.nombre_zona = None

    def retrieve_provinces(self):
        """Obtener la lista de provincias desde el sitio web."""
        url = self.base_url + '/ProvinceSelector.aspx'
        if self.options.verbose:
            print('Retrieving %s ... ' % url)
        try:
            response = json.load(self.opener.open(url))
        except:
            print('No locations found online.')
            print('Maybe the website is offline or it has been recently redesigned.')
            return {}
        else:
            return [x.values()[0] for x in response['rows']]

    def retrieve_locations(self, province):
        """Obtener la lista de localidades desde el sitio web."""
        locations = {}
        url = self.base_url + '/LocalitySelector.aspx?province=' + quote_plus(province)
        if self.options.verbose:
            print('Retrieving %s ... ' % url)
        try:
            response = json.load(self.opener.open(url))
        except:
            print('No locations found online.')
            print('Maybe the website is offline or it has been recently redesigned.')
            return locations
        else:
            for row in response['rows']:
                locations[int(row['Id'])] = row
            if self.options.verbose:
                print('Found %d locations available.' % len(locations))
            return locations

    def retrieve_channels(self):
        """Obtener la lista de canales desde el sitio web."""
        channels = {}
        url = self.base_url + '/index.aspx'
        if self.codigo_zona is not None:
            url += '?cl=%d' % self.codigo_zona
        if self.options.verbose:
            print('Retrieving %s ... ' % url, file = sys.stderr)
        try:
            body = html.parse(self.opener.open(url))
        except:
            print('No channels found online.', file = sys.stderr)
            print('Maybe the website is offline or it has been recently redesigned.', file = sys.stderr)
            return channels
        grilla = body.find(".//select[@id='ChannelChoice']")
        hidden_digClasId = body.find(".//input[@id='digClasId']")
        hidden_digHd = body.find(".//input[@id='digHd']")
        hidden_idsChanels = body.find(".//input[@id='idsChanels']")
        hidden_sintoniaChanels = body.find(".//input[@id='sintoniaChanels']")
        if grilla is None or hidden_digClasId is None or hidden_digHd is None or \
           hidden_idsChanels is None or hidden_sintoniaChanels is None:
            print('No channels found online.', file = sys.stderr)
            print('Maybe the website is offline or it has been recently redesigned.', file = sys.stderr)
            return channels
        self.digClasId = hidden_digClasId.get('value')
        self.digHd = 1 if hidden_digHd.get('value') != 'true' else 2
        idsChanels = [int(n) for n in hidden_idsChanels.get('value').split(',')]
        sintoniaChanels = [int(n) for n in hidden_sintoniaChanels.get('value').split(',')]
        sintonia = dict(zip(idsChanels, sintoniaChanels))
        for elem in grilla.iterdescendants('option'):
            channid = int(elem.get('value'))
            if channid < 0: continue
            channel = XmltvChannel(channid, sintonia[channid], elem.text.strip())
            channels[channel.id] = channel
        # parsear las descripciones y los iconos, que si bien no es
        # necesario, lo hago por completitud
        grilla = body.find(".//div[@id='grilla']")
        if grilla is not None:
            for elem in grilla[0]:
                channid = int(elem.get('id'))
                img = elem.find('.//img')
                channels[channid].icon = img.get('src')
                channels[channid].description = img.get('alt').strip()
        if self.options.verbose:
            print('Found %d channels online.' % len(channels), file = sys.stderr)
        return channels

    def retrieve_days(self, channels, firstDay):
        """Obtener la grilla de programacion de varios dias para los canales
        indicados, a partir de la fecha dada.
        """
        nchannels = len(channels)
        nbatch = 12
        programs = []
        currentday  = datetime.combine(firstDay, time(0,0,0))
        currentday += timedelta(days=self.options.offset)
        for nday in range(self.options.offset, self.options.offset + self.options.days):
            i = 0
            while i < nchannels:
                # obtener la informacion de a lotes de canales
                batch = channels[i:i+nbatch]
                try:
                    programs += self.retrieve_day(batch, nday, currentday)
                except urllib2.HTTPError as e:
                    # ante algun error de HTTP, intentar canal por canal
                    for channel in batch:
                        try:
                            programs += self.retrieve_day([channel], nday, currentday)
                        except urllib2.HTTPError as e:
                            s_print('HTTP error: %s ' % str(e), file = sys.stderr)
                except urllib2.URLError as e:
                    # ante otro error, omitir la programacion de la misma
                    s_print('URL error: %s ' % str(e), file = sys.stderr)
                i += nbatch
            currentday += timedelta(days=1)
        if self.options.verbose:
            print('Found %d programs.' % len(programs), file = sys.stderr)
        return programs

    def retrieve_day(self, batch, nday, currentday):
        """Obtener los programas en todas las bandas horarias del dia."""
        programs = []
        for hourSel in xrange(1, 8):
            programs += self.retrieve_grid(batch, nday, currentday, hourSel)
        return programs

    def json_request(self, url, request_body):
        """Realizar una peticion JSON e interpretar el resultado."""
        headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json; charset=utf-8',
            'Referer': self.base_url,
            'Content-Length': len(request_body),
        }
        req = urllib2.Request(url, request_body, headers)
        return json.load(self.opener.open(req))

    def retrieve_grid(self, batch, nday, currentday, hoursel):
        """Obtener la grilla de programacion para una serie de canales, un dia
        y una banda horaria determinada.
        """
        # hoursel va de 1 a 6, donde 1 = 00:00, 2 = 04:00, y asi...
        signalsIdsReceived  = ','.join(str(c.id) for c in batch) + '|'
        signalsIdsReceived += ','.join(str(c.number) for c in batch)
        request_body = json.dumps({
            'daySel': str(nday),
            'clasDigId': self.digClasId,
            'signalsIdsReceived': signalsIdsReceived,
            'digHd': self.digHd,
            'hourSel': hoursel,
            'sitio': '',
        })
        url = '/TVGridWS/TvGridWS.asmx/ReloadGrid'
        if self.options.verbose:
            # print >> sys.stderr, request_body
            print('Retrieving %s - %s' % (url, request_body), file = sys.stderr)
        response = self.json_request(self.base_url + url, request_body)
        sleep(SLEEP_TIME)
        programs = []
        rows = html.fragment_fromstring(response['d'], True)
        for row in rows:
            programs += self.parse_row_data(currentday, row)
        return programs

    def get_program_data(self, channelid, currentday, accordion):
        """Obtiene los datos de un programa."""
        # cada acordeon es una emision de un show
        if len(accordion) == 0: return None
        prog = self.parse_program(channelid, currentday, accordion)
        if prog is not None: return prog
        else: return None

    def parse_row_data(self, currentday, row):
        """Interpretar las celdas de un renglon de la grilla de programacion."""
        programs = []
        # channelId = int(remove_letters(row.get('id')))
        if row.get('idsignal') is None:
            return programs
        channelid = int(row.get('idsignal'))
        # Necesario para poder ejecutar funciones con varios parametros de manera concurrente
        parcializado = partial(self.get_program_data, channelid, currentday)
        programs = global_pool.map(parcializado, row)
        return programs

    def parse_program(self, channelid, startday, div):
        """Interpretar un programa de television indicado en una celda de la
        grilla de programacion.
        """
        prog = XmltvProgram()
        prog.channel = channelid
        title = div[0].cssselect("span")[0].text.strip()
        prog.title = fix_encoding(title)
        prog.ficha = int(remove_letters(div.get('id')))
        style = parse_style(div.get('style'))
        left = max(0, int(remove_letters(style['left'])))
        width = max(0, int(remove_letters(style['width'])))
        prog.starthour = int(left * TvGrabAr.TIME_CONST)
        prog.duration = int(width * TvGrabAr.TIME_CONST)
        try:
            programStartHour = datetime.strptime(sec_to_hour(prog.starthour), '%H:%M')
            programDuration = datetime.strptime(sec_to_hour(prog.duration), '%H:%M')
        except ValueError:
            return None
        prog.start = datetime.combine(startday.date(), programStartHour.time())
        # conversion de zona horaria
        prog.start = prog.start.replace(tzinfo=self.input_timezone)
        prog.start = prog.start.astimezone(self.output_timezone)
        # fin conversion de zona horaria
        prog.stop = prog.start + timedelta(hours=programDuration.hour, minutes=programDuration.minute)
        if not self.options.skip_descriptions:
            self.retrieve_descriptions(prog, div)
        return prog

    def retrieve_fichacontent(self, url, tupla):
        """Recuperar e interpretar la informacion contenida en una ficha de
        programa.
        """
        # url = '/FichaContent.aspx?id=%d&idSig=%d' % tupla          # metodo 2
        data = { 'url': self.base_url + url }
        try:
            sleep(SLEEP_TIME)
            body = html.parse(self.opener.open(self.base_url + url))
        except urllib2.HTTPError as e:
            # ante algun error al obtener la descripcion, omitirla
            s_print('HTTP error: %s ' % str(e), file = sys.stderr)
            return {}
        except urllib2.URLError as e:
            # ante algun error al obtener la descripcion, omitirla
            s_print('URL error: %s ' % str(e), file = sys.stderr)
            return {}
        except socket_error as e:
            # ante algun error al obtener la descripcion, omitirla
            s_print('Socket error: %s ' % str(e), file = sys.stderr)
            return {}
        divFicha = body.find(".//div[@class='ficha']/div/div")
        if divFicha is None:
            return {}
        for elem in divFicha.iter():
            class_ = elem.get('class')
            if class_ is None:
                continue
            text = None
            if elem.text:
                text = fix_encoding(elem.text)
            if elem.tag == 'a':
                if 'resumenFicha' in class_:
                    data['resumenFicha'] = text
                elif 'tituloItemFicha' in class_:
                    current_key = text.strip(':')
                    if current_key not in (u'G\xe9nero', u'Actores', u'Pa\xeds', u'A\xf1o', u'Director'):
                        raise RuntimeError(u'Unhandled program data: %s' % current_key)
                elif 'detalleItemFicha' in class_:
                    data[current_key] = text
                elif 'nombreActorFicha' in class_:
                    if current_key not in data:
                        data[current_key] = []
                    data[current_key].append(text.strip(', '))
                elif 'lb_gallery' in class_:
                    if 'lb_gallery' not in data:
                        data['lb_gallery'] = []
                    data['lb_gallery'].append(elem[0].get('src'))
            elif elem.tag == 'div':
                if 'tituloFicha' in class_:
                    data['tituloFicha'] = fix_encoding(elem[0].tail).strip()
            elif elem.tag == 'img':
                if 'chapaParentalProgramFicha' in class_:
                    src = self.base_url + '/' + elem.get('src')
                    rating, _ = basename(src).split('.')
                    data['chapaParentalProgramFicha'] = (rating, elem.get('title'), src)
        return data

    def retrieve_descriptions(self, prog, div):
        """Obtener la informacion adicional, tal como descripcion, actores, etc
        de un programa de television, ya sea desde el cache o pidiendolo por 
        la red.
        """
        # obtener los datos que se pueden tomar directamente (titleSeason, titleChapter)
        data = {}
        for elem in div.iter():
            class_ = elem.get('class')
            text = None
            if elem.text:
                text = fix_encoding(elem.text)
            if class_ is not None and elem.tag == 'span' and text is not None:
                data[class_] = text
        # hay dos alternativas para obtener las descripciones
        # 1. hacer una peticion POST a /TVGridWS/TvGridWS.asmx/GetProgramDataAcordeon
        #    parsear el JSON y obtener los datos de la ficha breve
        # 2. hacer una peticion GET a /FichaContent.aspx?id={prog.ficha}&idSig={prog.channel}
        #    parsear el HTML y obtener los datos de la ficha completa
        if not prog.ficha: return
        tupla = (prog.ficha, prog.channel)
        # url = '/TVGridWS/TvGridWS.asmx/GetProgramDataAcordeon'   # metodo 1
        url = '/FichaContent.aspx?id=%d&idSig=%d' % tupla          # metodo 2
        if tupla in self.fichas:
            # si la respuesta ya estaba en el cache
            if self.options.verbose:
                s_print('Skipping %s ...' % url, file = sys.stderr)
            (prog.description, prog.data) = self.fichas[tupla]
            prog.data.update(data)
            # tratar de obtener el titulo completo del show
            if 'tituloFicha' in prog.data:
                prog.title = completar_titulo(prog.title, prog.data['tituloFicha']);
            return
        # si la respuesta no estaba en cache
        if self.options.verbose:
            s_print('Retrieving %s ...' % url, file = sys.stderr)
        # metodo 1
        # por eficiencia y por lo sencillo de la estructura no uso json.dumps
        # request_body = '{"idEvent": "%d", "idSignal": "%d", "sitio": ""}' % (prog.ficha, prog.channel)
        # response = self.json_request(self.base_url + url, request_body)
        # if response is None: return
        # body = html.fragment_fromstring(response['d'], True)
        # data.update(self.parse_getprogramdataacordeon(body))
        # fin metodo 1
        # metodo 2
        remote_data = self.retrieve_fichacontent(url, tupla)
        if not remote_data:
            return
        data.update(remote_data)
        prog.data = data
        # tratar de obtener el titulo completo del show
        if 'tituloFicha' in prog.data:
            prog.title = completar_titulo(prog.title, prog.data['tituloFicha']);
        # incorporar la descripcion, si existe
        if 'resumenFicha' in data:
            prog.description = data['resumenFicha']
        elif u'G\xe9nero' in data:
            prog.description = data[u'G\xe9nero']
        self.fichas[tupla] = (prog.description, prog.data)

    def select_channels(self):
        """Solicitar al usuario los canales que desea recuperar."""
        channels = self.retrieve_channels()
        chanlist = channels.values()
        chanlist = sorted(chanlist, key=cmp_to_key(lambda x,y: x.number - y.number))
        add_all = False
        skip_all = False
        for channel in chanlist:
            prompt = 'add channel %s [yes, no, all, none] ? ' % str(channel)
            if not add_all and not skip_all:
                reply = None
                while reply not in ['y', 'yes', 'n', 'no', 'all', 'none', '']:
                    reply = raw_input(prompt).strip().lower()
                if reply == '' or reply == 'y' or reply == 'yes':
                    channel.enabled = True
                elif reply == 'n' or reply == 'no':
                    channel.enabled = False
                elif reply == 'all':
                    channel.enabled = True
                    add_all = True
                elif reply == 'none':
                    channel.enabled = False
                    skip_all = True
            elif add_all:
                channel.enabled = True
                print(prompt + 'yes')
            elif skip_all:
                channel.enabled = False
                print(prompt + 'no')
        return chanlist

    def select_location(self):
        """Solicitar al usuario la localidad para la cual desea recuperar la
        programacion.
        """
        provinces = self.retrieve_provinces()
        if not provinces: return
        selected = None
        while selected < 0 or selected >= len(provinces):
            for code, name in enumerate(provinces):
                print("%2d. %-30s  " % (code+1, name[:30]))
            try:
                selected = int(raw_input('enter your province code: ')) - 1
            except ValueError:
                pass
        locations = self.retrieve_locations(provinces[selected])
        if not locations: return
        ordenadas = sorted(locations.items(), key=lambda x: x[1]['Localidad'])
        selected = None
        while selected not in locations:
            c = r = 0
            for code, row in ordenadas:
                c += 1
                r += 1
                print("%4d. %-30s  " % (int(code), row['Localidad'][:30]),)
                if c == 2:
                    print
                    c = 0
                if r == 46:
                    raw_input('more below -- press Enter key to continue ')
                    r = 0
            print
            try:
                selected = int(raw_input('enter your location code: '))
            except ValueError:
                pass
        self.codigo_zona = selected
        self.nombre_zona = locations[selected]['Localidad']
        print('selected location: %4d. %s' % (selected, self.nombre_zona))

    def configure(self):
        """Configurar el script."""
        if not isdir(dirname(self.options.config_file)):
            mkdir(dirname(self.options.config_file))
        conf = codecs.open(self.options.config_file, 'w', 'UTF-8')
        self.select_location()
        conf.write(u'location %d %s\n' % (self.codigo_zona, self.nombre_zona))
        chanlist = self.select_channels()
        for channel in chanlist:
            if not channel.enabled: conf.write('#')
            conf.write(u'channel %d %s\n' % (channel.id, channel.name))
        conf.close()
        print('Finished configuration.')

    def set_enabled_channels(self, channels):
        """Leer del archivo de configuracion la lista de canales activos para
        descarga.
        """
        for id_ in channels:
            channels[id_].enabled = False
        enabled = 0
        if not isdir(dirname(self.options.config_file)):
            mkdir(dirname(self.options.config_file))
        if not isfile(self.options.config_file):
            return False
        for line in open(self.options.config_file):
            (chan, id_, name) = line.split(' ', 2)
            if chan != 'channel': continue
            enabled += 1
            if int(id_) in channels:
                channels[int(id_)].enabled = True
        if self.options.verbose:
            print('Found %d channels enabled.' % enabled, file = sys.stderr)
        return True

    def sort_programs(self, programs):
        """Ordenar una lista de programas segun su hora de inicio."""
        
        # Quitamos elementos nulos para evitar excepciones
        programs = [program for program in programs if program != None]
        return sorted(programs, key=cmp_to_key(lambda x,y: int((x.start - y.start).total_seconds())))

    def count_programs(self, channels, programs):
        """Contar la cantidad de programas de cada canal."""
        for id_, channel in channels.items():
            channel.num_programs = 0
        for prog in programs:
            channels[prog.channel].num_programs += 1

    def load_fichas(self):
        """Leer las fichas de descripcion de los programas desde el cache."""
        if not isdir(dirname(self.options.cache_file)):
            mkdir(dirname(self.options.cache_file))
        for ntry in range(3):
            if self.options.verbose:
                print('Reading program card cache ... ', file = sys.stderr)
            try:
                fh = open(self.options.cache_file, 'rb')
                self.fichas = cPickle.load(fh)
                fh.close()
            except (EOFError, cPickle.UnpicklingError):
                # verificar si es posible restaurar un backup
                base, ext = splitext(self.options.cache_file)
                fichasbak = base + '.bak'
                if isfile(fichasbak):
                    if self.options.verbose:
                        print('corrupt file, using backup', file = sys.stderr)
                        copy(fichasbak, self.options.cache_file)
                else:
                    if self.options.verbose:
                        print('corrupt file, discarded', file = sys.stderr)
                    rename(self.options.cache_file, base + '.old')
            except IOError:
                if self.options.verbose:
                    print('could not load %s' % self.options.cache_file, file = sys.stderr)
                break
            else:
                if self.options.verbose:
                    print('%d programs known.' % len(self.fichas), file = sys.stderr)
                break

    def save_fichas(self):
        """Guardar las fichas de descripcion de los programas en el cache."""
        if not isdir(dirname(self.options.cache_file)):
            mkdir(dirname(self.options.cache_file))
        if self.options.verbose:
            print('Saving program card cache ... ', file = sys.stderr)
        try:
            fh = open(self.options.cache_file, 'wb')
            cPickle.dump(self.fichas, fh)
            fh.close()
            if self.options.verbose:
                print('done.', file = sys.stderr)
            # backup del archivo de fichas
            base, ext = splitext(self.options.cache_file)
            copy(self.options.cache_file, base + '.bak')
        except IOError:
            if self.options.verbose:
                print('could not write %s' % self.options.cache_file, file = sys.stderr)

    def grab(self):
        """Descargar informacion de programacion."""
        startdate = datetime.today().strftime(DATETIME_FMT)
        if self.codigo_zona is None: self.get_config_zona()
        if self.options.verbose:
            print('Getting list of channels', file = sys.stderr)
        channels = self.retrieve_channels()
        if not self.set_enabled_channels(channels):
            print("Please run './tv_grab_ar.py --configure' first.", file = sys.stderr)
            print('', file = sys.stderr)
            return

        xml = Writer(
            encoding='UTF-8',
            datestr=startdate,
            source_info_url=self.base_url,
            source_info_name=self.base_url,
            generator_info_name='tv_grab_ar.py/' + VERSION,
            generator_info_url='http://maurom.com/blog/2010/02/03/tvtime-xmltv-tv_grab_ar-py'
        )

        ordenados = sorted(channels.values(), key=cmp_to_key(lambda x,y: x.number - y.number))
        if self.options.list_channels:
            # informar todos los canales, ordenados por numero
            for channel in ordenados:
                xml.addChannel(channel.get_dict())
        else:
            self.load_fichas()
            # obtener la lista de canales activos
            enabled = [c for c in ordenados if c.enabled]
            programs = self.retrieve_days(enabled, date.today())
            programs = self.sort_programs(programs)
            self.save_fichas()
            self.count_programs(channels, programs)
            # informar solo los canales con programas agendados
            for channel in ordenados:
                if channel.num_programs == 0: continue
                xml.addChannel(channel.get_dict())
            for program in programs:
                xml.addProgramme(program.get_dict())

        if self.options.output:
            xml.writetofile(self.options.output)
        else:
            print(xml.tostring())


if __name__ == '__main__':
    reload(sys)
    if sys.version_info.major == 2: sys.setdefaultencoding('utf-8')

    parser = argparse.ArgumentParser(
        description='Get Argentinian television listings in XMLTV format'
    )
    parser.add_argument('--days', type=int, dest='days', default=3, metavar='N',
        help='Grab N days.  The default is 3.')
    parser.add_argument('--offset', type=int, dest='offset', default=0, metavar='N',
        help='Start N days in the future.  The default is to start from today.')
    parser.add_argument('--skip-descriptions', action='store_true', dest='skip_descriptions', default=False,
        help='Do not download program descriptions.')
    parser.add_argument('--output',  dest='output', metavar='FILE',
        help='Write to FILE rather than standard output.')
    parser.add_argument('--configure', action='store_true', dest='configure',
        help='Prompt for which channels and write the configuration file.')
    parser.add_argument('--config-file',  dest='config_file', metavar='FILE',
        default=join(XMLTV_CONFIG_DIR, 'tv_grab_ar.conf'),
        help='Set the name of the configuration file, the default is <' + join(XMLTV_CONFIG_DIR, 'tv_grab_ar.conf') + '>.  This is the file written by --configure and read when grabbing.')
    parser.add_argument('--quiet', action='store_true', dest='quiet', default=False,
        help='Suppress the progress messages normally written to standard error. [not implemented]')
    parser.add_argument('--verbose', action='store_true', dest='verbose', default=False,
        help='Display additional information.')
    parser.add_argument('--list-channels', action='store_true', dest='list_channels',
        help='Display only the channel listing.')
    parser.add_argument('--zone', type=int, dest='codigo_zona', metavar='N',
        help='Override user location for retrieval of channels.')
    parser.add_argument('--capabilities', action='store_true', dest='capabilities',
        help='Show which capabilities the grabber supports.  For more information, see <http://wiki.xmltv.org/index.php/XmltvCapabilities>')
    parser.add_argument('--describe', action='store_true', dest='description',
        help='Show a brief description of the grabber.')
    parser.add_argument('--description', action='store_true', dest='description',
        help='Show a brief description of the grabber.')
    parser.add_argument('--cache', dest='cache_file', metavar='FILE',
        default=join(XMLTV_CONFIG_DIR, 'tv_grab_ar.db'),
        help='Cache description data in FILE. The default is <' + join(XMLTV_CONFIG_DIR, 'tv_grab_ar.db') + '>.')
    parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION)

    args = parser.parse_args()
    if args.days < 0: parser.error('number of days must not be negative')
    if args.offset < 0: parser.error('offset must not be negative')

    if args.verbose:
        print('tv_grab_ar.py %s\n' % VERSION, file = sys.stderr)

    app = TvGrabAr()
    app.options = args

    if args.capabilities:
        app.capabilities()
    elif args.description:
        app.description()
    elif args.configure:
        app.configure()
    else:
        global_pool = ThreadPool(processes=THREADS, initializer=None)
        app.grab()

