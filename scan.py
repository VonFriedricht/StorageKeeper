import pyautogui
import time
from PIL import Image
import keyboard
import imagehash
import json
import os
import cv2
import numpy as np
import mouse  # Für die Maussteuerung

speed1 = 0.1
speed2 = 0.1
speed3 = 0.2

# Funktion zum Laden der bekannten Hashes aus einer JSON-Datei
def load_known_hashes(json_file):
    if os.path.exists(json_file):
        with open(json_file, 'r') as file:
            return json.load(file)
    else:
        return {}

# Funktion zum Speichern der bekannten Hashes in einer JSON-Datei
def save_known_hashes(json_file, known_hashes):
    with open(json_file, 'w') as file:
        json.dump(known_hashes, file, indent=4)

# Funktion zum Screenshot machen und speichern
def capture_screenshot(region_number):
    # Screenshot des gesamten Bildschirms
    screenshot = pyautogui.screenshot()

    # Bereich definieren (704, 276) mit Breite 528 und Höhe 264
    left = 704
    top = 276
    width = 528
    height = 264
    box = (left, top, left + width, top + height)

    # Den Bereich zuschneiden und speichern
    region = screenshot.crop(box)
    filename = f"region_{region_number}.png"
    region.save(filename)
    print(f"Screenshot {filename} von Kiste {region_number} gespeichert.")
    return region

# Funktion, um aus jedem Slot einen relevanten Bildausschnitt zu extrahieren
def extract_relevant_area(image, slot_x, slot_y):
    left = slot_x  # Start direkt am Anfang des Slots
    top = slot_y   # Start direkt am Anfang des Slots
    right = left + 72  # 72 Pixel Breite
    bottom = top + 48  # 48 Pixel Höhe
    return image.crop((left, top, right, bottom))

# Funktion, um den braunen Hintergrund zu entfernen
def remove_brown_background(image):
    image_array = np.array(image)

    brown_tones = [
        [48, 33, 12],   # 30210c
        [49, 34, 17],   # 312211
        [48, 32, 12],   # 30200c
        [49, 32, 12],   # 31200c
        [48, 32, 12]    # 30200c (wiederholt)
    ]

    tolerance = 20

    for tone in brown_tones:
        lower_bound = np.array([max(0, tone[0] - tolerance), max(0, tone[1] - tolerance), max(0, tone[2] - tolerance)])
        upper_bound = np.array([min(255, tone[0] + tolerance), min(255, tone[1] + tolerance), min(255, tone[2] + tolerance)])

        mask = cv2.inRange(image_array, lower_bound, upper_bound)

        image_array[mask != 0] = [255, 255, 255]  # Ersetze mit Weiß

    processed_image = Image.fromarray(image_array)
    return processed_image

# Funktion, um die Shift+Linksklick-Aktion im Inventar durchzuführen
def shift_click_inventory(slot):
    """
    Simuliert Shift+Linksklick im Inventar auf den entsprechenden Slot.
    Das Inventar fängt bei 528,592 an. Die Slots sind 88 Pixel voneinander entfernt.
    """
    inventory_x = 528
    inventory_y = 592

    # Berechne die Position des Slots im Inventar (1-based index)
    row = (slot - 1) // 10
    col = (slot - 1) % 10
    click_x = inventory_x + col * 88 + 44  # Mitte des Slots in X
    click_y = inventory_y + row * 88 + 44  # Mitte des Slots in Y

    # Shift+Linksklick auf den berechneten Slot
    mouse.move(click_x, click_y, absolute=True)
    pyautogui.keyDown('shift')
    time.sleep(0.1)  # Warten nach dem Drücken von Shift
    mouse.click(button='left')
    time.sleep(0.1)  # Warten vor dem Loslassen von Shift
    pyautogui.keyUp('shift')

# Funktion, um die Shift+Linksklick-Aktion in den Kisten durchzuführen
def shift_click_chest(slot_x, slot_y):
    """
    Simuliert Shift+Linksklick auf einen bestimmten Slot in der aktuellen Kiste.
    """
    mouse.move(704 + slot_x + 36, 276 + slot_y + 24, absolute=True)
    pyautogui.keyDown('shift')
    time.sleep(0.1)  # Warten nach dem Drücken von Shift
    mouse.click(button='left')
    time.sleep(0.1)  # Warten vor dem Loslassen von Shift
    pyautogui.keyUp('shift')

# Funktion, um die Hashes des Inventargrids zu erfassen und Items zu verschieben
def inventory_to_hashes(image, region_number, file, known_hashes):
    slot_width = 88
    slot_height = 88
    rows = 3
    cols = 6

    file.write(f"Kiste {region_number}:\n")

    for row in range(rows):
        for col in range(cols):
            slot_x = col * slot_width
            slot_y = row * slot_height

            relevant_area = extract_relevant_area(image, slot_x, slot_y)
            processed_image = remove_brown_background(relevant_area)

            slot_hash = str(imagehash.phash(processed_image))

            if slot_hash in known_hashes:
                item_info = known_hashes[slot_hash]
                if ',' in item_info:
                    expected_kiste, item_name = item_info.split(',', 1)
                else:
                    expected_kiste = None
                    item_name = item_info

                if expected_kiste and int(expected_kiste) != region_number:
                    print(f"Item '{item_name}' gehört in Kiste {expected_kiste}, ist aber in Kiste {region_number}.")
                    print("Item wird ins Inventar verschoben.")
                    shift_click_chest(slot_x, slot_y)  # Item ins Inventar verschieben
                    items_to_move.append((item_name, int(expected_kiste)))  # Merke, welches Item wohin soll
                else:
                    print(f"Item '{item_name}' ist in der richtigen Kiste ({region_number}).")
            else:
                item_name = f"Unknown Item (Hash: {slot_hash})"
                unknown_image_filename = f"{slot_hash}.png"
                processed_image.save(unknown_image_filename)
                print(f"Unbekanntes Item als {unknown_image_filename} gespeichert.")

            file.write(f"  Slot {row * cols + 1}: {item_name}\n")

# Funktion, um die eingesammelten Items in die korrekten Kisten zu legen
def place_items_in_correct_chest():
    """
    Nachdem Items ins Inventar verschoben wurden, sollen sie in die korrekten Kisten verschoben werden.
    items_to_move enthält die Information, welches Item in welche Kiste soll.
    """
    global current_chest  # Verwende die globale Variable für die aktuelle Kiste
    global items_to_move  # Verwende die globale items_to_move-Liste

    # Prüfe, welche die erste Kiste ist, in die ein Item verschoben werden muss
    if items_to_move:
        first_chest_needed = items_to_move[0][1]
        print(f"Das erste Item gehört in Kiste {first_chest_needed}.")
    else:
        print("Keine Items zu verschieben.")
        return

    # Wenn der Bot nicht bei der ersten benötigten Kiste ist, bewege ihn dorthin
    while current_chest != first_chest_needed:
        move_to_chest(current_chest, first_chest_needed)
        current_chest = first_chest_needed

    print(f"Beginne mit dem Platzieren der Items ab Kiste {first_chest_needed}.")
    
    for i, (item_name, kiste) in enumerate(items_to_move):
        print(f"Verschiebe Item '{item_name}' in Kiste {kiste}.")

        # Wenn sich das Item in einer anderen Kiste befindet, wechsle die Kiste
        if current_chest != kiste:
            move_to_chest(current_chest, kiste)
            current_chest = kiste

        print(f"Öffne Kiste {current_chest}.")
        mouse.move(960, 700, absolute=True)  # Maus auf die Position der Kiste bewegen
        time.sleep(0.1)
        pyautogui.press('e')  # Kiste öffnen
        time.sleep(0.5)  # Warte nach dem Öffnen der Kiste

        shift_click_inventory(i + 1)  # Item im Inventar verschieben (z.B. Slot 1, 2, ...)
        pyautogui.press('e')  # Kiste schließen
        time.sleep(0.5)  # Warte nach dem Schließen der Kiste

    # Liste items_to_move leeren für den nächsten Durchlauf
    items_to_move.clear()
    print("Items-to-move-Liste geleert.")

# Funktion, um zwischen Kisten zu wechseln
def move_to_chest(current_chest, target_chest):
    steps = abs(target_chest - current_chest)
    
    if current_chest < target_chest:
        print(f"Bewege von Kiste {current_chest} zu Kiste {target_chest} (+{steps}).")
        for _ in range(steps):
            # W und D gleichzeitig drücken (Bewegung zu +1 Kiste)
            pyautogui.keyDown('w')
            time.sleep(0.1)
            pyautogui.keyDown('d')
            time.sleep(0.1)
            pyautogui.keyUp('w')
            pyautogui.keyUp('d')
    
            # S und A gleichzeitig drücken
            pyautogui.keyDown('a')
            time.sleep(0.1)
            pyautogui.keyDown('s')
            time.sleep(0.1)
            pyautogui.keyUp('s')
            pyautogui.keyUp('a')
    elif current_chest > target_chest:
        print(f"Bewege von Kiste {current_chest} zu Kiste {target_chest} (-{steps}).")
        for _ in range(steps):
            # D und W gleichzeitig drücken (Bewegung zu -1 Kiste)
            pyautogui.keyDown('d')
            time.sleep(0.1)
            pyautogui.keyDown('w')
            time.sleep(0.1)
            pyautogui.keyUp('w')
            pyautogui.keyUp('d')

            # A und S gleichzeitig drücken
            pyautogui.keyDown('s')
            time.sleep(0.1)
            pyautogui.keyDown('a')
            time.sleep(0.1)
            pyautogui.keyUp('s')
            pyautogui.keyUp('a')

# Funktion, die das Tastendrücken und die Screenshots verwaltet
def main_script():
    global current_chest  # Verwende die globale Variable für die aktuelle Kiste
    global items_to_move  # Verwende die globale items_to_move-Liste
    current_chest = 9  # Initialer Start bei Kiste 9
    items_to_move = []  # Initialisiere die Liste für jedes Script-Rennen neu

    while True:  # Endlosschleife für den Loop
        # Known Hashes jedes Mal neu laden
        known_hashes = load_known_hashes('known_hashes.json')

        with open('inventory_all_regions.txt', 'w') as file:
            for i in range(1, 10):  # Für jede der 10 Kisten
                print(f"Starte Scan von Kiste {i}.")

                # Bewege die Maus zur Position (960, 700), um sicherzustellen, dass der Spieler die Kiste ansieht
                mouse.move(960, 700, absolute=True)
                time.sleep(0.5)

                # E drücken, um die Kiste zu öffnen
                pyautogui.press('e')
                time.sleep(speed3)

                # Screenshot machen und speichern (region_1.png, region_2.png, usw.)
                image = capture_screenshot(i)
                inventory_to_hashes(image, i, file, known_hashes)

                # Nochmal E drücken nach dem Screenshot, um die Kiste zu schließen
                pyautogui.press('e')
                time.sleep(speed3)

                # Zur nächsten Kiste wechseln
                if i < 9:  # Nur zur nächsten Kiste wechseln, wenn es noch eine gibt
                    move_to_chest(i, i + 1)
                    current_chest = i + 1

            # Alle eingesammelten Items in die richtigen Kisten verschieben
            place_items_in_correct_chest()

            # Zurück zu Kiste 1
            print("Zurück zu Kiste 1.")
            move_to_chest(current_chest, 1)

            # Optional: Wartezeit vor der nächsten Runde einfügen
            print("Wartezeit vor der nächsten Runde...")
            time.sleep(5)  # Warte 5 Sekunden vor dem nächsten Durchlauf

print("Drücke 'J', um das Skript zu starten.")
keyboard.wait('j')

main_script()

save_known_hashes('known_hashes.json', load_known_hashes('known_hashes.json'))
