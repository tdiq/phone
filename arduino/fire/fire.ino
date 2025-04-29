#include <FastLED.h>
#include "FastLED_RGBW.h"

enum Mode {
  OFF,
  FIRE_ON
};

#define DATA_PIN     3
#define COLOR_ORDER GRB
#define CHIPSET     WS2812B
#define NUM_LEDS    160

#define BRIGHTNESS  128
#define FRAMES_PER_SECOND 30


#define COOLING  55 
#define SPARKING 120 
bool gReverseDirection = false;

CRGBW leds[NUM_LEDS];
CRGB *ledsRGB = (CRGB *) &leds[0];


Mode currentMode = OFF;

void setup() {
  Serial.begin(9600);
	FastLED.addLeds<WS2812B, DATA_PIN, RGB>(ledsRGB, getRGBWsize(NUM_LEDS));
  FastLED.setBrightness( BRIGHTNESS );
  fill_solid_rgbw(CRGB::Green);
  FastLED.show();
  testLEDS();
  currentMode = FIRE_ON;
  Serial.println("Ready for blinkenlights");
}

void loop(){  
  if (Serial.available() > 0) {
    String message = Serial.readStringUntil('\n');
    message.trim();
    
    if (message == "L1") {
      currentMode = FIRE_ON;
      Serial.println("Light ON");
    }
    else if (message == "L0") {
      currentMode = OFF;
      fill_solid_rgbw(CRGB::Black);
      Serial.println("Light OFF");
    }
    else if (message == "S1") {
      Serial.println("Smoke ON");
    }
    else if (message == "S0") {
      Serial.println("Smoke OFF");
    }
    else {
      Serial.print("Unknown command: ");
      Serial.println(message);
    }
  }

  if (currentMode == FIRE_ON) {
    random16_add_entropy( random());
    Fire2012();
    FastLED.show();
    FastLED.delay(1000 / FRAMES_PER_SECOND);
  }
}


void fill_solid_rgbw( const CRGB color) {
  for( int i = 0; i < NUM_LEDS; i++) {
      leds[i] = color;
    }
    FastLED.show();
}

void testLEDS() {
  fill_solid_rgbw(CRGB::Red);
  FastLED.show();
  delay(1000);
  fill_solid_rgbw(CRGB::Green);
  FastLED.show();
  delay(1000);
  fill_solid_rgbw(CRGB::Blue);
  FastLED.show();
  delay(1000);
  fill_solid_rgbw(CRGB::Black);
  FastLED.show();
}

void Fire2012() {

// Array of temperature readings at each simulation cell
  static byte heat[NUM_LEDS];

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
