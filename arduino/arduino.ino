#include <Arduino.h>
#include <FastLED.h>

enum Mode {
  OFF,
  FIRE_ON
};

const int LIGHT_PIN = LED_BUILTIN;  // Light control pin
const int SMOKE_PIN = 12;           // Smoke machine control pin
const int LED_PIN = 13;             // LED strip pin

#define COLOR_ORDER GRB
#define CHIPSET     WS2812
#define NUM_LEDS    30
#define BRIGHTNESS  200
#define FRAMES_PER_SECOND 60

#define COOLING  55 
#define SPARKING 120 
bool gReverseDirection = false;

CRGB leds[NUM_LEDS];
Mode currentMode = OFF;


void setup() {
  Serial.begin(9600);
  pinMode(LIGHT_PIN, OUTPUT);
  pinMode(SMOKE_PIN, OUTPUT);
  digitalWrite(LIGHT_PIN, LOW);
  digitalWrite(SMOKE_PIN, LOW);

  FastLED.addLeds<CHIPSET, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS).setCorrection( TypicalLEDStrip );
  FastLED.setBrightness( BRIGHTNESS );

  Serial.println("Controller ready!");
}

void loop() {
  // Check if data is available to read
  if (Serial.available() > 0) {
    // Read the incoming message
    String message = Serial.readStringUntil('\n');
    message.trim();  // Remove any whitespace/newlines
    
    // Process the message
    if (message == "L1") {
      digitalWrite(LIGHT_PIN, HIGH);
      currentMode = FIRE_ON;
      Serial.println("Light ON");
    }
    else if (message == "L0") {
      digitalWrite(LIGHT_PIN, LOW);
      currentMode = OFF;
      Serial.println("Light OFF");
    }
    else if (message == "S1") {
      digitalWrite(SMOKE_PIN, HIGH);
      Serial.println("Smoke ON");
    }
    else if (message == "S0") {
      digitalWrite(SMOKE_PIN, LOW);
      Serial.println("Smoke OFF");
    }
    else {
      Serial.print("Unknown command: ");
      Serial.println(message);
    }
  }

  // Run fire effect if in FIRE_ON mode
  if (currentMode == FIRE_ON) {
    Fire2012();
    FastLED.show();
    FastLED.delay(1000 / FRAMES_PER_SECOND);
  }
}



void Fire2012()
{
// Array of temperature readings at each simulation cell
  static uint8_t heat[NUM_LEDS];

  // Step 1.  Cool down every cell a little
    for( int i = 0; i < NUM_LEDS; i++) {
      heat[i] = qsub8( heat[i],  random8(0, ((COOLING * 10) / NUM_LEDS) + 2));
    }
  
    // Step 2.  Heat from each cell drifts 'up' and diffuses a little
    for( int k= NUM_LEDS - 1; k >= 2; k--) {
      heat[k] = (heat[k - 1] + heat[k - 2] + heat[k - 2] ) / 3;
    }
    
    // Step 3.  Randomly ignite new 'sparks' of heat near the bottom
    if( random8() < SPARKING ) {
      int y = random8(7);
      heat[y] = qadd8( heat[y], random8(160,255) );
    }

    // Step 4.  Map from heat cells to LED colors
    for( int j = 0; j < NUM_LEDS; j++) {
      CRGB color = HeatColor( heat[j]);
      int pixelnumber;
      if( gReverseDirection ) {
        pixelnumber = (NUM_LEDS-1) - j;
      } else {
        pixelnumber = j;
      }
      leds[pixelnumber] = color;
    }
}