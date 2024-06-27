import cv2
import numpy as np
import tensorflow as tf
import serial
import time

def check_camera(index=0):
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        print("Error: No se pudo abrir la cámara.")
        return None
    return cap

def load_model(model_path):
    print("Cargando el modelo...")
    model = tf.saved_model.load(model_path)
    print("Modelo cargado.")
    return model

def detect_objects(model, frame, conf_threshold=0.5):
    input_tensor = tf.convert_to_tensor(frame)
    input_tensor = input_tensor[tf.newaxis, ...]

    detections = model(input_tensor)
    detection_scores = detections['detection_scores'][0].numpy()
    detection_classes = detections['detection_classes'][0].numpy().astype(np.int32)
    detection_boxes = detections['detection_boxes'][0].numpy()

    (h, w) = frame.shape[:2]

    max_score = 0
    max_index = -1

    for i in range(detection_scores.shape[0]):
        if detection_scores[i] > conf_threshold and detection_classes[i] == 17:  # ID para gatos en COCO dataset
            if detection_scores[i] > max_score:
                max_score = detection_scores[i]
                max_index = i

    if max_index != -1:
        box = detection_boxes[max_index] * np.array([h, w, h, w])
        (startY, startX, endY, endX) = box.astype("int")
        label = f"Cat: {max_score:.2f}"
        cv2.rectangle(frame, (startX, startY), (endX, endY), (0, 0, 255), 2) 
        y = startY - 15 if startY - 15 > 15 else startY + 15
        cv2.putText(frame, label, (startX, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)  

        if max_score > conf_threshold:
            print("Gato detectado con una confianza de: ", max_score)
            return True, frame

    return False, frame

def main():
    cap = check_camera()
    if not cap:
        return

    try:
        arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=1)  # Ajusta '/dev/ttyACM0' al puerto correcto de tu Arduino
        time.sleep(2)  # Espera a que la conexión serial se establezca
        print("Conexión serial establecida.")
    except serial.SerialException as e:
        print(f"No se pudo abrir el puerto serial: {e}")
        return

    model_path = "/home/juan/models/ssd_mobilenet_v2_fpnlite_320x320/ssd_mobilenet_v2_fpnlite_320x320_coco17_tpu-8/saved_model"  # Path to your TensorFlow saved model
    model = load_model(model_path)

    last_sent_time = time.time()
    debounce_time = 2  # Segundos de espera entre comandos

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: No se pudo capturar la imagen de la cámara.")
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  
        detected, frame = detect_objects(model, frame_rgb)

        current_time = time.time()
        if detected and (current_time - last_sent_time > debounce_time):
            print("Enviando comando al Arduino...")
            arduino.write(b'M')  # Enviar comando al Arduino
            last_sent_time = current_time

        cv2.imshow("Frame", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    arduino.close()
    print("Conexión serial cerrada.")

if __name__ == "__main__":
    main()
