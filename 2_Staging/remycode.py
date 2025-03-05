import time
import board
from adafruit_clue import clue
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService
import displayio
import terminalio
from adafruit_display_text import label

# Initialize BLE
ble = BLERadio()
uart = UARTService()
advertisement = ProvideServicesAdvertisement(uart)

# Initialize display
display = board.DISPLAY
group = displayio.Group()
display.root_group = group

# Function to display text on the screen
def display_text(message):
    # Clear the display group
    while len(group) > 0:
        group.pop()
    # Create a label with the message
    text_label = label.Label(terminalio.FONT, text=str(message), color=0xFFFFFF, x=0, y=10)
    group.append(text_label)

# Function to play a beep sound
def play_beep():
    clue.play_tone(1000, 0.5)

# Function to play a celebration tune
def play_music():
    # Made some music
    melody = [
        (262, 0.3),  # C4
        (330, 0.3),  # E4
        (392, 0.3),  # G4
        (523, 0.6),  # C5
        (392, 0.3),  # G4
        (523, 0.6)   # C5
    ]
    for note in melody:
        frequency, duration = note
        clue.play_tone(frequency, duration)
        time.sleep(0.1)

# RemyAI Class
class RemyAI:
    def __init__(self):
        self.ingredients = []
        self.recipes = {
            "pasta": [
                "1. Mince the garlic finely.",
                "2. Heat olive oil with garlic.",
                "3. Boil water with a pinch of salt.",
                "4. Cook pasta 8-10 mins.",
                "5. Add spinach until wilted.",
                "6. Mix pasta w/ the spinach&garlic.",
                "7. Add Parmesan cheese"
            ],
            "salad": [
                "1. Wash spinach.",
                "2. Chop other veggies.",
                "3. Toss everything in a large bowl.",
                "4. Feta cheese and olives.",
                "5. Olive oil and balsamic vinegar."
            ],
            "bake": [
                "1. Preheat the oven to 375°F (190°C).",
                "2. Mix spinach, feta cheese, and eggs.",
                "3. Add a pinch of salt and pepper.",
                "4. Put them into a baking dish.",
                "5. Bake for 25-30 minutes.",
                "6. Cool for 5 minutes!"
            ]
        }
        self.wine_pairings = {
            "pasta": "Chianti",
            "salad": "Sauvignon Blanc",
            "bake": "Pinot Noir"
        }

    def sniff(self, ingredients):
        self.ingredients = ingredients
        display_text("Remy sniffs: " + ", ".join(ingredients))

    def suggest(self):
        if "spinach" in self.ingredients:
            display_text("Try: pasta, salad, or bake.")
        else:
            display_text("Need more ingredients!")

    def cook(self, recipe):
        if recipe in self.recipes:
            for step in self.recipes[recipe]:
                display_text(step)
                play_beep()  # Play beep as a reminder
                while True:
                    if clue.button_a:
                        time.sleep(0.5)  # anti-shaking
                        break
            # Recommend wines and play music
            wine = self.wine_pairings.get(recipe, "a glass of wine")
            display_text(f"Food is done！Enjoy with {wine}")
            play_music()  # Play celebration music
        else:
            display_text("Recipe not found.")

# Main Program
remy = RemyAI()
ble.start_advertising(advertisement)
display_text("RemyAI is ready!")

while True:
    if ble.connected:
        if uart.in_waiting > 0:  # Ensure there is data in the buffer
            try:
                command = uart.read(uart.in_waiting).strip().decode("utf-8")
                print("Received command:", command)
                if command == "sniff":
                    remy.sniff(["spinach", "garlic", "pasta"])
                elif command == "suggest":
                    remy.suggest()
                elif command.startswith("cook"):
                    try:
                        recipe = command.split(" ")[1]
                        remy.cook(recipe)
                    except IndexError:
                        display_text("Usage: cook <recipe>")
                elif command == "reset":
                    remy = RemyAI()
                    display_text("Remy is ready!")
                else:
                    display_text("Unknown command.")
            except Exception as e:
                print("Error:", e)
                display_text("Error processing command.")
    else:
        if not ble.advertising:
            ble.start_advertising(advertisement)
    time.sleep(0.1)
