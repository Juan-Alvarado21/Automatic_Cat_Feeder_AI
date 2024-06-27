#include <Servo.h>

Servo miServo;

void setup() {
  Serial.begin(9600);  // Inicia la comunicación serial a 9600 bps
  Serial.println("Iniciado y en reposo");
  miServo.attach(9);   // Adjunta el servo al pin 9 al inicio
  miServo.write(0);    // Asegúrate de que el servo esté en 0 grados (reposo)
}

void loop() {
  if (Serial.available() > 0) {
    char comando = Serial.read();
    Serial.print("Comando recibido: ");
    Serial.println(comando);
    if (comando == 'M') {
      moverServo();
    }
  } else {
    miServo.write(0);  // Asegura que el servo esté en reposo si no hay comandos
  }
}

void moverServo() {
  Serial.println("Moviendo el servo a 45 grados");
  miServo.write(15);   // Mueve el servo a 45 grados
  delay(1000);         // Espera 1 segundo para asegurar que el servo llegue a 45 grados
  Serial.println("Regresando el servo a 0 grados");
  miServo.write(0);    // Devuelve el servo a 0 grados (reposo)
  delay(1000);         // Espera 1 segundo para asegurar que el servo regrese a 0 grados
  Serial.println("Servo en reposo");
}
