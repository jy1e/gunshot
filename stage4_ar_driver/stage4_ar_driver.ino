#include <ArduinoJson.h>

const int trigPin = A0;
const int echoPin = A1;
const int irPin = A4;

void setup() {
    Serial.begin(9600);
    pinMode(trigPin, OUTPUT);
    pinMode(echoPin, INPUT);
    pinMode(irPin, INPUT);
}

int readUltrasonic() {
    digitalWrite(trigPin, LOW);
    delayMicroseconds(2);
    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);
    long duration = pulseIn(echoPin, HIGH);
    return duration * 0.034 / 2;
}

void loop() {
    if (Serial.available() > 0) {
        String raw = Serial.readStringUntil('\n');
        JsonDocument doc;
        DeserializationError error = deserializeJson(doc, raw);

        if (error) {
            Serial.println("{\"error\":\"error\"}");
            return;
        }

        String cmd = doc["cmd"];
        int ultrasonic = readUltrasonic();
        bool ir = digitalRead(irPin) == LOW;

        JsonDocument res;

        if (cmd == "forward" || cmd == "backward" || cmd == "left" || cmd == "right") {
            res["state"] = "moving";
            res["direction"] = cmd;
            res["ultrasonic"] = ultrasonic;
            res["ir"] = ir;
        } else if (cmd == "stop") {
            res["state"] = "stopped";
            res["direction"] = "none";
            res["ultrasonic"] = ultrasonic;
            res["ir"] = ir;
        } else {
            res["error"] = "error";
        }

        serializeJson(res, Serial);
        Serial.println();
    }
}