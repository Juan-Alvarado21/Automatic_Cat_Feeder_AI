import paramiko
from scp import SCPClient
import subprocess
import os
import time
import signal
import atexit

def obtenerSiguienteNumero():
    with open("count.txt", "r") as f:
        return int(f.read())

def aumentarNumero():
    prev = obtenerSiguienteNumero()
    with open("count.txt", "w") as f:
        prev += 1
        f.write(str(prev))

def tomar_y_guardar_foto(ssh, scp, frames, sig):
    # Cambiar la resolución de la foto si es necesario
    tomarFoto = f"fswebcam -S 10 -d /dev/video0 -r 1920x1080 -F {frames} /home/juan/out.png"
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(tomarFoto)
    print(ssh_stdout.read().decode()) # Necesario para el procesamiento lazy

    # Copiar el archivo al dispositivo local
    scp.get('/home/juan/out.png', './img/out.png')

    # Guardar la foto con un nombre numérico y eliminar fotos antiguas
    if sig >= retener:
        archivo_a_borrar = f'./img/{sig - retener}.png'
        if os.path.exists(archivo_a_borrar):
            os.remove(archivo_a_borrar)

    # Renombrar y guardar la foto actual
    os.rename('./img/out.png', f'./img/{sig}.png')

def limpiar_fotos():
    for archivo in os.listdir('./img'):
        if archivo.endswith('.png'):
            os.remove(os.path.join('./img', archivo))
    print("Todas las fotos han sido borradas.")

# Establecer usuario, host y password
#usuario=
#contraseña 
#password

# Conectar al servidor SSH
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=usuario, password=contrasenia)
scp = SCPClient(ssh.get_transport())

# Configuración inicial
frames = 10  # Disminuye el ruido
retener = 5  # Número de fotos que se retienen en el dispositivo

# Registrar la función de limpieza para que se ejecute al salir
atexit.register(limpiar_fotos)

def signal_handler(sig, frame):
    print('Programa interrumpido, limpiando fotos...')
    limpiar_fotos()
    ssh.close()
    exit(0)

signal.signal(signal.SIGINT, signal_handler)

while True:
    sig = obtenerSiguienteNumero()
    tomar_y_guardar_foto(ssh, scp, frames, sig)
    aumentarNumero()
    time.sleep(1)  # Esperar 1 segundo antes de tomar la siguiente foto
