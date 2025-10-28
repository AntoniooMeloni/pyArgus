// Define os pinos do sensor
const int trigPin = 8;
const int echoPin = 9;

void setup() {
  // Inicializa comunicação serial
  Serial.begin(9600);
  
  // Define os pinos como saída e entrada
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
}

void loop() {
  // Garante que o trig esteja desligado
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  
  // Envia pulso de 10 microssegundos
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  // Lê o tempo que o pulso levou para ir e voltar
  long duration = pulseIn(echoPin, HIGH);
  
  // Calcula a distância em centímetros
  float distance = duration * 0.034 / 2;

  // Imprime a distância
  Serial.println(distance);

  // Aguarda um pouco antes da próxima leitura
  delay(500);
}
