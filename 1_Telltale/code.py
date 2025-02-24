import time
import board
import displayio
import terminalio
from adafruit_display_text import label
from adafruit_clue import clue
import adafruit_apds9960.apds9960

# **Initialize Display**
display = board.DISPLAY
display.auto_refresh = False  # Prevent flickering

# **Create display groups**
text_group = displayio.Group()
image_group = displayio.Group()

# **Background Color (Dark Blue)**
background = displayio.Bitmap(display.width, display.height, 1)
palette = displayio.Palette(1)
palette[0] = 0x000033  # Dark blue background
background_sprite = displayio.TileGrid(background, pixel_shader=palette)
text_group.append(background_sprite)  # Add background first

# **Title Label (Centered)**
title_label = label.Label(terminalio.FONT, text="Litter Box Activity", scale=2, color=0xFFFFFF)
title_label.anchor_point = (0.5, 0)
title_label.anchored_position = (display.width // 2, 10)

# **Status Label**
status_label = label.Label(terminalio.FONT, text="Idle", scale=2, color=0x0000FF)  # Blue for Idle
status_label.anchor_point = (0.5, 0)
status_label.anchored_position = (display.width // 2, 50)

# **Session Info Labels**
last_session_label = label.Label(terminalio.FONT, text="Last: --", scale=2, color=0xFFD700)  # Gold
last_session_label.anchor_point = (0.5, 0)
last_session_label.anchored_position = (display.width // 2, 90)

time_since_label = label.Label(terminalio.FONT, text="Since: --", scale=2, color=0x00FF00)  # Green
time_since_label.anchor_point = (0.5, 0)
time_since_label.anchored_position = (display.width // 2, 130)

uses_label = label.Label(terminalio.FONT, text="Uses: --/5", scale=2, color=0xFF4500)  # Orange
uses_label.anchor_point = (0.5, 0)
uses_label.anchored_position = (display.width // 2, 170)

# **Progress Bar**
progress_width = 100  # Adjust size
progress_bar = displayio.Bitmap(progress_width, 10, 2)
progress_palette = displayio.Palette(2)
progress_palette[0] = 0x444444  # Dark gray (empty)
progress_palette[1] = 0x00FF00  # Green (filled)
progress_sprite = displayio.TileGrid(progress_bar, pixel_shader=progress_palette, x=(display.width // 2) - 50, y=200)

# **Add Elements to Display Group**
text_group.append(title_label)
text_group.append(status_label)
text_group.append(last_session_label)
text_group.append(time_since_label)
text_group.append(uses_label)
text_group.append(progress_sprite)

# **Load Clean & Dirty Images**
try:
    clean_bitmap = displayio.OnDiskBitmap("/clean.bmp")
    dirty_bitmap = displayio.OnDiskBitmap("/dirty.bmp")
    image_view = displayio.TileGrid(clean_bitmap, pixel_shader=clean_bitmap.pixel_shader)
    image_group.append(image_view)
except Exception as e:
    print(f"❌ ERROR: BMP loading failed - {e}")

# **Set initial display state**
display.root_group = text_group
display.refresh()

# **Initialize Proximity Sensor**
i2c = board.I2C()
proximity_sensor = adafruit_apds9960.apds9960.APDS9960(i2c)
proximity_sensor.enable_proximity = True

# **Increase Sensitivity Settings**
proximity_sensor.proximity_gain = 3  # Max sensitivity
proximity_sensor.led_drive = 3  # Max LED strength

# **Thresholds & Constants**
PROXIMITY_MOVEMENT_THRESHOLD = 5  
MOVEMENT_RESET_TIME = 30  
STILLNESS_CONFIRMATIONS_REQUIRED = 15  
MAX_SESSIONS_BEFORE_CLEAN = 5  

# **Session Tracking Variables**
session_start_time = None
last_session_duration = 0
time_since_last_session = 0
last_session_end_time = time.monotonic()
total_sessions = 0
movement_detected = False
stillness_counter = 0
current_mode = "summary"
waiting_for_stillness = False
stopwatch_time = 0  

print("📏 Measuring initial baseline... Keep the box completely still.")
time.sleep(3)

# **Step 1: Measure Initial Baseline Value**
def calibrate_baseline():
    global baseline_proximity
    baseline_proximity = proximity_sensor.proximity
    print(f"📏 Baseline Updated: Proximity={baseline_proximity}")

calibrate_baseline()  

# **Function to Update Progress Bar**
def update_progress_bar():
    progress_bar.fill(0)  
    filled_width = int((total_sessions / MAX_SESSIONS_BEFORE_CLEAN) * progress_width)
    for x in range(filled_width):
        progress_bar[x, 0] = 1  

# **Function to Update Summary**
def update_summary():
    last_session_label.text = f"Last: {last_session_duration:.0f}s"
    time_since_label.text = f"Since: {time_since_last_session:.0f}s"
    uses_label.text = f"Uses: {total_sessions}/5"

    update_progress_bar()
    display.root_group = text_group
    display.refresh()

# **Function to Update Clean/Dirty Image**
def update_image():
    try:
        while len(image_group) > 0:
            image_group.pop()  # Remove previous image safely

        new_image = displayio.TileGrid(
            clean_bitmap if total_sessions < 5 else dirty_bitmap,
            pixel_shader=clean_bitmap.pixel_shader,
        )

        image_group.append(new_image)
        display.root_group = image_group
        display.refresh()
    except Exception as e:
        print(f"❌ ERROR: Display update failed - {e}")

# **Main Loop**
while True:
    proximity_value = proximity_sensor.proximity
    proximity_change = abs(proximity_value - baseline_proximity)

    if not movement_detected and proximity_change >= PROXIMITY_MOVEMENT_THRESHOLD:
        print("🐱 Penny Entered!")
        session_start_time = time.monotonic()
        movement_detected = True
        last_movement_time = time.monotonic()
        stillness_counter = 0
        waiting_for_stillness = False  
        status_label.text = "In Use"
        status_label.color = 0x00FF00  # Green
        display.refresh()

    if movement_detected and (time.monotonic() - last_movement_time) > MOVEMENT_RESET_TIME:
        if proximity_change < PROXIMITY_MOVEMENT_THRESHOLD:
            stillness_counter += 1
            print(f"🔍 Stillness detected {stillness_counter}/{STILLNESS_CONFIRMATIONS_REQUIRED}...")
            if stillness_counter >= STILLNESS_CONFIRMATIONS_REQUIRED:
                print("✅ Litter box is now still!")
                last_session_duration = time.monotonic() - session_start_time
                time_since_last_session = time.monotonic() - last_session_end_time
                total_sessions += 1
                update_summary()
                status_label.text = "Idle"
                status_label.color = 0x0000FF  # Blue
                movement_detected = False
                calibrate_baseline()

        else:
            stillness_counter = 0  

    if clue.button_b:
        update_image()
        current_mode = "image"

    if clue.button_a:
        update_summary()
        current_mode = "summary"

    time.sleep(0.2)
