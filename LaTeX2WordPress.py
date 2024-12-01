# Paquetes necesarios
import os
import re
import requests
import json
import sys
from dotenv import load_dotenv
import base64
import time 

## Función para convertir un archivo LaTeX a HTML usando Pandoc
def LaTeX2HTML(archivo):
    """
    Convierte un archivo LaTeX en HTML utilizando Pandoc.
    Realiza reemplazos en el texto para ajustar el formato al estándar HTML esperado.
    
    Args:
        archivo (str): Ruta del archivo LaTeX a convertir.
    
    Returns:
        str: Tema extraído del archivo LaTeX.
    """
    # Leer el contenido del archivo LaTeX
    with open(archivo, "r", encoding='utf8') as f:
        texto = f.read()

    # Extraer el tema del archivo
    patron = r'\\tema\{(.*)\}'
    tema = re.search(patron, texto).group(1)

    # Realizar los reemplazos necesarios en el contenido
    texto = texto.replace('{preguntas}', '{enumerate}')
    texto = texto.replace('begin{respuesta}', 'begin{proof}[Solución]')
    texto = texto.replace('end{respuesta}', 'end{proof}')
    texto = texto.replace(r'\ref', r'\\ref')
    texto = texto.replace(r'\tema', r'\title')
    texto = texto.replace(r'\autor', r'\author')
    texto = texto.replace(r'\fecha', r'\date')

    # Guardar el archivo modificado temporalmente
    archivo_temp = archivo.replace(".tex", "_temp.tex")
    with open(archivo_temp, "w", encoding='utf8') as f:
        f.write(texto)

    # Convertir el archivo temporal a HTML usando Pandoc
    archivo_html = archivo.replace(".tex", ".html")
    os.system(f"pandoc {archivo_temp} -s --mathjax -o {archivo_html}")

    # Leer el archivo HTML generado
    with open(archivo_html, "r", encoding='utf8') as f:
        texto = f.read()

    # Realizar ajustes finales al contenido HTML
    texto = texto.replace('<em>Proof.</em>', '<strong>Demostración.</strong>')
    texto = texto.replace('<em>Solución.</em>', '<strong>Solución.</strong>')
    texto = texto.replace('\n<div class="proof">', '<br>\n<div class="proof">')
    texto = texto.replace('<div class="ejer">\n<p>', '<div class="ejer"><p><strong>Ejercicio. </strong>')
    texto = texto.replace(r'\sen', r'\sin')
    texto = texto.replace(r'\setlength{\arraycolsep}{2pt}', r'')
    texto = texto.replace('~◻', '').replace(' ◻', '')

    # Extraer el contenido dentro de la etiqueta <body>
    patron = r'<body>(.*)</body>'
    texto = re.search(patron, texto, re.DOTALL).group(1)

    # Quitar el header HTML no deseado
    patron = r'\n<header[^>]*>.*?</header>'
    texto = re.sub(patron, '', texto, flags=re.DOTALL)

    # Formatear el contenido para mayor legibilidad
    texto = texto.replace('<span class="math display">', '\n<span class="math display">\n')
    texto = texto.replace('<li>', '\t<li>')
    texto = texto.replace('<tr ', '\t<tr ')
    texto = texto.replace('<div class="proof">\n<p>', '<div class="proof">\n\t<p>')

    # Sobreescribir el archivo HTML con los cambios realizados
    with open(archivo_html, "w", encoding='utf8') as f:
        f.write(texto)

    # Eliminar el archivo temporal
    os.remove(archivo_temp)

    # Devolver el tema extraído
    return tema

## Función para publicar contenido en WordPress
def postWordPress(html, tema, portada):
    """
    Publica un contenido en WordPress utilizando la API REST.
    Primero sube una imagen de portada, luego crea un post con contenido HTML y una imagen destacada.
    
    Args:
        html (str): Ruta del archivo HTML con el contenido.
        tema (str): Título de la publicación.
        portada (str): Ruta de la imagen de portada.
    """
    # Configuración de la API
    api_url = "https://alephsub0.org/wp-json/wp/v2/media"
    url = "https://alephsub0.org/wp-json/wp/v2/posts"
    load_dotenv()
    usuario = os.getenv("USUARIO")
    contraseña = os.getenv("CONTRASENIA")
    auth = (usuario, contraseña)
    print(f"Usuario: {os.getenv('USUARIO')}")

    # Subir la imagen de portada
    headers = {
        "Content-Disposition": "attachment; filename=Portada.jpeg",
        "Content-Type": "image/jpeg",
    }
    # with open(portada, "rb") as img:
    #     response = requests.post(api_url, headers=headers, auth=auth, data=img)

    # # Verificar si la imagen fue subida exitosamente
    # if response.status_code == 201:  # Código 201 = Creado
    #     media_id = response.json()["id"]
    #     print(f"Imagen subida exitosamente. ID: {media_id}")
    # else:
    #     print("Error al subir la imagen:", response.text)
    #     return

    # Leer el contenido HTML
    with open(html, "r", encoding='utf8') as f:
        texto = f.read()

    # Preparar los datos de la publicación
    headers = {"Content-Type": "application/json"}
    data = {
        "title": tema,
        "content": texto,
        "status": "draft",  # Opciones: 'publish', 'draft', etc.
        "categories": [4],  # IDs de las categorías
        "tags": [1],  # IDs de las etiquetas
        # "featured_media": media_id,  # ID de la imagen destacada
    }

    # Enviar la solicitud POST para crear la publicación
    response = requests.post(url, headers=headers, auth=auth, data=json.dumps(data))

    # Verificar si la publicación fue creada exitosamente
    if response.status_code == 201:  # Código 201 indica éxito
        print("Publicación creada con éxito.")
    else:
        print("Error al crear la publicación:", response.status_code, response.text)


## Funciones para incluir ip en Cloudflare


def obtener_ip_publica():
    """Obtiene la IP pública del dispositivo
    
    returns:
    str: IP pública del dispositivo
    """

    try:
        respuesta = requests.get('https://api.ipify.org?format=json')
        ip_publica = respuesta.json()['ip']
        return ip_publica
    except requests.RequestException as err:
        print(f"Error obteniendo la IP pública: {err}")
        return None
    
def insertar_regla_ip(ip,tipo="whitelist",comentario="Script"):
    """Inserta una regla de acceso en Cloudflare

    Referecias: https://developers.cloudflare.com/api/operations/ip-access-rules-for-a-zone-create-an-ip-access-rule

    Args:
    ip (str): Dirección IP a insertar
    tipo (str): Tipo de regla (whitelist o blacklist)
    comentario (str): Comentario de la regla
    
    returns:
    str: Identificador de la regla creada
    """

    payload = {  
        "configuration": 
            {
                "target": "ip",
                "value": ip
            },  
        "mode": tipo, 
        "notes": comentario
    }

    response = requests.request("POST", url_cloudflare, headers=headers_clouflare, json=payload)

    respuesta = response.json()

    # verificamos si respuesta tiene una clave success con valor true
    if respuesta.get("success"):
        return respuesta['result']['id']
    else:
        raise Exception(f"Error al insertar la regla: {respuesta}")

def eliminar_regla_ip(identificador_regla):

    """
    Elimina una regla de acceso en Cloudflare

    Referecias: https://developers.cloudflare.com/api/operations/ip-access-rules-for-a-zone-delete-an-ip-access-rule

    Args:
    identificador_regla (str): Identificador de la regla a eliminar

    returns:
    bool: True si la regla fue eliminada exitosamente
    """

    url = f"https://api.cloudflare.com/client/v4/zones/{zona_id}/firewall/access_rules/rules/{identificador_regla}"

    response = requests.request("DELETE", url, headers=headers_clouflare)

    respuesta = response.json()

    if respuesta.get("success"):
        return True
    else:
        raise Exception(f"Error al eliminar la regla: {respuesta}")

# Punto de entrada del script
if __name__ == "__main__":
    # Leer argumentos de la línea de comandos
    archivo = sys.argv[1]
    portada = sys.argv[2]

    usuario_serv = os.getenv("USUARIO_SERV")
    contraseña_serv = os.getenv("CONTRASENIA_SERV")
    credenciales = f"{usuario_serv}:{contraseña_serv}"
    credenciales_en_base64 = base64.b64encode(credenciales.encode("utf-8")).decode("utf-8")

    zona_id = os.getenv("CLOUDFLARE_ZONE_ALEPH")

    headers_clouflare = {
        "Content-Type": "application/json",
        "X-Auth-Email": os.getenv("CLOUDFLARE_CORREO"),
        "X-Auth-Key": os.getenv("CLOUDFLARE_TOKEN")
    }

    url_cloudflare = f"https://api.cloudflare.com/client/v4/zones/{zona_id}/firewall/access_rules/rules"

    print(f"Convirtiendo {archivo} a HTML y publicando en WordPress...")
    print(f"Usuario: {os.getenv('USUARIO')}")
    print(f"Usuario servidor: {os.getenv('USUARIO_SERV')}")
    print(f"URL: {url_cloudflare}")

    # Insertamos la regla para el firewall
    identificador_regla = insertar_regla_ip(obtener_ip_publica(),tipo="whitelist",comentario="Github Actions")
    # esperar
    time.sleep(2)

    # Convertir LaTeX a HTML y publicar en WordPress
    tema = LaTeX2HTML(archivo)
    postWordPress(archivo.replace(".tex", ".html"), tema, portada)

    # Esperar 1 segundo
    time.sleep(1)
    # Eliminar la regla del firewall
    eliminar_regla_ip(identificador_regla)