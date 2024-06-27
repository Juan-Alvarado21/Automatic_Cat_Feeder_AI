from flask import Flask, send_from_directory, render_template_string, jsonify, request
import os
from glob import glob
from datetime import datetime, timedelta
import time as t
import json
import threading
import serial
import jwt as pyjwt  
import cv2
import numpy as np
import tensorflow as tf

app = Flask(__name__)

# RUTA DEL DIRECTORIO
IMAGE_FOLDER = r"/home/juan/detector/img"
MODEL_PATH = "/home/juan/models/ssd_mobilenet_v2_fpnlite_320x320/ssd_mobilenet_v2_fpnlite_320x320_coco17_tpu-8/saved_model"

# Generar tokens
SECRET_KEY = 'your_secret_key'

# Intervalos de alimentación
FEEDING_INTERVALS = []  # Se agregarán dinámicamente

# Cargar modelo de detección
model = None
def load_model(model_path):
    print("Cargando el modelo...")
    global model
    model = tf.saved_model.load(model_path)
    print("Modelo cargado.")

def get_latest_image():
    """Devuelve la imagen más reciente en la carpeta."""
    images = glob(os.path.join(IMAGE_FOLDER, '*'))
    if not images:
        return None
    latest_image = max(images, key=os.path.getctime)
    return latest_image

def detect_cat_in_image(image_path):
    """Detecta si hay un gato en la imagen especificada."""
    frame = cv2.imread(image_path)
    if frame is None:
        return False
    
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    input_tensor = tf.convert_to_tensor(frame_rgb)
    input_tensor = input_tensor[tf.newaxis, ...]

    detections = model(input_tensor)
    detection_scores = detections['detection_scores'][0].numpy()
    detection_classes = detections['detection_classes'][0].numpy().astype(np.int32)
    detection_boxes = detections['detection_boxes'][0].numpy()

    max_score = 0
    for i in range(detection_scores.shape[0]):
        if (detection_scores[i] > 0.5 and detection_classes[i] == 17):
            if detection_scores[i] > max_score:
                max_score = detection_scores[i]

    return max_score > 0.5

@app.route('/image')
def image():
    """Sirve la imagen más reciente."""
    latest_image = get_latest_image()
    if (latest_image):
        return send_from_directory(IMAGE_FOLDER, os.path.basename(latest_image))
    return '', 404

@app.route('/latest_image_path')
def latest_image_path():
    """Devuelve la ruta de la imagen más reciente."""
    latest_image = get_latest_image()
    if latest_image:
        return jsonify({'image_path': os.path.basename(latest_image)})
    return jsonify({'image_path': None}), 404

@app.route('/')
def index():
    """Renderiza la página HTML principal."""
    token = generate_token()
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Cat Feeder</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                background-color: #f0f0f0;
            }
            header {
                background-color: rgb(88, 211, 140);
                color: white;
                padding: 20px;
                text-align: center;
                font-size: 2em;
                font-weight: bold;
            }
            .container {
                display: flex;
                height: calc(100vh - 60px);
            }
            .menu {
                flex: 1;
                padding: 20px;
                background-color: #fff;
                border-right: 1px solid #ccc;
                overflow-y: auto;
            }
            .content {
                flex: 2;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
                background-color: #e9ecef;
            }
            img {
                max-width: 100%;
                max-height: 100%;
                object-fit: contain;
                border: 1px solid #ccc;
                border-radius: 8px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            }
            button, input {
                padding: 10px 20px;
                font-size: 16px;
                cursor: pointer;
                margin-top: 10px;
                border: none;
                border-radius: 5px;
            }
            input[type=time] {
                width: calc(100% - 24px);
                margin-bottom: 10px;
                padding: 10px;
                font-size: 16px;
                border: 1px solid #ccc;
                border-radius: 5px;
                background-color: #fff;
                color: #333;
            }
            button {
                background-color: rgb(88, 211, 140);
                color: white;
            }
            .alert {
                padding: 20px;
                background-color: #f44336;
                color: white;
                margin-bottom: 15px;
            }
            .closebtn {
                margin-left: 15px;
                color: white;
                font-weight: bold;
                float: right;
                font-size: 22px;
                line-height: 20px;
                cursor: pointer;
                transition: 0.3s;
            }
            .closebtn:hover {
                color: black;
            }
            .clock {
                font-size: 24px;
                margin-bottom: 10px;
            }
            .time-label {
                font-weight: bold;
                margin-bottom: 5px;
            }
            .expired {
                color: red;
            }
        </style>
    </head>
    <body>
        <header>Cat Feeder</header>
        <div class="container">
            <div class="menu">
                <h2>Configuración de Alimentación</h2>
                <div id="feedingTimesContainer"></div>
                <div class="time-input">
                    <div class="time-label">Hora inicio:</div>
                    <input type="time" id="startTime" />
                </div>
                <div class="time-input">
                    <div class="time-label">Hora fin:</div>
                    <input type="time" id="endTime" />
                </div>
                <button onclick="addFeedingInterval()">Agregar Intervalo de Alimentación</button>
                <button onclick="feedCat()">Alimentar Manualmente</button>
                <button onclick="closeProgram()">Cerrar Programa</button>
                <h3>Tiempo para la próxima comida:</h3>
                <p id="timeUntilNextFeed" class="clock"></p>
                <h3>Estado de Alimentación:</h3>
                <p id="feedingStatus">Inactivo</p>
                <h3>Estado del Token:</h3>
                <p id="tokenStatus">Activo</p>
            </div>
            <div class="content">
                <img id="latestImage" src="" alt="Imagen más reciente">
            </div>
        </div>
        <script>
            let feedingIntervals = {{ feeding_intervals|tojson }};
            let feedingActive = false;
            let tokenExpiration = new Date('{{ token["exp"] }}' * 1000);

            function updateFeedingIntervals() {
                const container = document.getElementById('feedingTimesContainer');
                container.innerHTML = '';
                feedingIntervals.forEach((interval, index) => {
                    container.innerHTML += `<p>${interval} <button onclick="removeFeedingInterval(${index})">Eliminar</button></p>`;
                });
                calculateTimeUntilNextFeed();
            }

            function addFeedingInterval() {
                const startTime = document.getElementById('startTime').value;
                const endTime = document.getElementById('endTime').value;
                if (startTime && endTime) {
                    const interval = `${startTime} a ${endTime}`;
                    feedingIntervals.push(interval);
                    updateFeedingIntervalsOnServer();
                }
            }

            function removeFeedingInterval(index) {
                feedingIntervals.splice(index, 1);
                updateFeedingIntervalsOnServer();
            }

            function updateFeedingIntervalsOnServer() {
                fetch('/feeding_intervals', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ feeding_intervals: feedingIntervals })
                }).then(response => {
                    if (response.ok) {
                        updateFeedingIntervals();
                    } else {
                        showAlert('Error al actualizar los intervalos de alimentación.');
                    }
                });
            }

            function calculateTimeUntilNextFeed() {
                const now = new Date();
                let nextFeedTime = null;
                feedingIntervals.forEach(interval => {
                    const [start, end] = interval.split(' a ');
                    const startTime = new Date();
                    const endTime = new Date();

                    startTime.setHours(parseInt(start.split(':')[0]), parseInt(start.split(':')[1]), 0);
                    endTime.setHours(parseInt(end.split(':')[0]), parseInt(end.split(':')[1]), 0);

                    if (now >= startTime && now <= endTime) {
                        nextFeedTime = endTime;
                    } else if (now < startTime && (!nextFeedTime || startTime < nextFeedTime)) {
                        nextFeedTime = startTime;
                    }
                });

                if (nextFeedTime) {
                    const diff = nextFeedTime - now;
                    const hours = Math.floor(diff / 3600000);
                    const minutes = Math.floor((diff % 3600000) / 60000);
                    document.getElementById('timeUntilNextFeed').textContent = `${hours}h ${minutes}m`;
                    feedingActive = now < nextFeedTime;
                } else {
                    document.getElementById('timeUntilNextFeed').textContent = 'No hay próximas comidas programadas.';
                    feedingActive = false;
                }
                updateFeedingStatus();
            }

            function updateImage() {
                fetch('/latest_image_path')
                    .then(response => response.json())
                    .then(data => {
                        if (data.image_path) {
                            const img = document.getElementById('latestImage');
                            img.src = `/image?${new Date().getTime()}`;
                        }
                    });
            }
            setInterval(updateImage, 1000);  // Actualiza cada segundo.

            function feedCat() {
                fetch('/feed', { method: 'POST' })
                    .then(response => {
                        if (response.ok) {
                            showAlert('El alimentador ha sido activado manualmente.');
                        } else {
                            showAlert('Error al activar el alimentador.');
                        }
                    });
            }

            function showAlert(message) {
                const alertDiv = document.createElement('div');
                alertDiv.className = 'alert';
                alertDiv.innerHTML = `${message} <span class="closebtn" onclick="this.parentElement.style.display='none';">&times;</span>`;
                document.body.insertBefore(alertDiv, document.body.firstChild);
                setTimeout(() => {
                    alertDiv.style.display = 'none';
                }, 3000);
            }

            function updateFeedingStatus() {
                document.getElementById('feedingStatus').textContent = feedingActive ? 'Activo' : 'Inactivo';
            }

            function closeProgram() {
                if (confirm('¿Estás seguro de que deseas cerrar el programa?')) {
                    fetch('/shutdown', { method: 'POST' })
                        .then(response => {
                            if (response.ok) {
                                window.close();
                            } else {
                                showAlert('Error al cerrar el programa.');
                            }
                        });
                }
            }

            function updateTokenStatus() {
                const now = new Date();
                const statusElement = document.getElementById('tokenStatus');
                if (now >= tokenExpiration) {
                    statusElement.textContent = 'Caducado';
                    statusElement.classList.add('expired');
                } else {
                    statusElement.textContent = 'Activo';
                    statusElement.classList.remove('expired');
                }
            }

            setInterval(updateTokenStatus, 1000);  // Comprobar estado del token cada segundo

            document.addEventListener('DOMContentLoaded', () => {
                updateFeedingIntervals();
                updateTokenStatus();
            });
        </script>
    </body>
    </html>
    ''', feeding_intervals=FEEDING_INTERVALS, token=generate_token())

@app.route('/shutdown', methods=['POST'])
def shutdown():
    """Endpoint para cerrar el programa."""
    os._exit(0)

def activate_feeder():
    """Lógica para activar el alimentador."""
    latest_image = get_latest_image()
    if latest_image and detect_cat_in_image(latest_image):
        try:
            arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
            t.sleep(2)  # Espera a que la conexión serial se establezca
            arduino.write(b'M')  # Comando para alimentar
            arduino.close()
            return True
        except serial.SerialException as e:
            print(f"No se pudo abrir el puerto serial: {e}")
            return False
    else:
        print("No se detectó un gato en la imagen más reciente.")
        return False

@app.route('/feed', methods=['POST'])
def feed():
    """Endpoint para alimentar manualmente al gato."""
    success = activate_feeder()
    if success:
        return '', 200
    else:
        return '', 500

@app.route('/feeding_intervals', methods=['POST'])
def update_feeding_intervals():
    """Endpoint para actualizar los intervalos de alimentación."""
    global FEEDING_INTERVALS
    data = request.get_json()
    FEEDING_INTERVALS = data.get('feeding_intervals', FEEDING_INTERVALS)
    return '', 200

def generate_token():
    """Genera un token JWT."""
    payload = {
        'exp': datetime.utcnow() + timedelta(minutes=30),
        'iat': datetime.utcnow(),
    }
    return pyjwt.encode(payload, SECRET_KEY, algorithm='HS256')

def validate_token(token):
    """Valida un token JWT."""
    try:
        pyjwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return True
    except pyjwt.ExpiredSignatureError:
        return False
    except pyjwt.InvalidTokenError:
        return False

@app.route('/token', methods=['GET'])
def get_token():
    """Endpoint para obtener un token."""
    return jsonify({'token': generate_token()})

def schedule_feeding():
    """Programa la alimentación automática."""
    while True:
        now = datetime.now()
        for interval in FEEDING_INTERVALS:
            start, end = interval.split(' a ')
            start_time = datetime.strptime(start, '%H:%M').time()
            end_time = datetime.strptime(end, '%H:%M').time()
            if start_time <= now.time() <= end_time and detect_cat_in_image(get_latest_image()):
                activate_feeder()
                t.sleep(60)  # Evita que se active varias veces
        t.sleep(1)

if __name__ == '__main__':
    load_model(MODEL_PATH)
    threading.Thread(target=schedule_feeding, daemon=True).start()
    app.run(debug=True)
