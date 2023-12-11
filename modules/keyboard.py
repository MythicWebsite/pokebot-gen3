from modules.context import context
from modules.memory import unpack_uint32, read_symbol
from modules.game import decode_string
from modules.tasks import task_is_active
from pathlib import Path
import math
import json

DATA_DIRECTORY = Path(__file__).parent / "data"

with open(f'{DATA_DIRECTORY}/keyboard.json', 'r', encoding='utf-8') as f:
    key_layout = json.load(f)

#Will have to add more languages later and detect it
lang = "en"

valid_characters = []
for num, page in enumerate(key_layout[lang]):
    for row in page["array"]:
        valid_characters.extend(row)


class Keyboard:
    def __init__(self):
        pass
    
    @property
    def enabled(self) -> bool:
        if task_is_active("Task_NamingScreen"):
            return True
        elif task_is_active("Task_NamingScreenMain"):
            return True
        else:
            return False
    
    @property
    def text_buffer(self) -> str:
        try:
            if context.rom.game_title not in ["POKEMON RUBY", "POKEMON SAPP"]:
                return decode_string(context.emulator.read_bytes(unpack_uint32(read_symbol("sNamingScreen")) + 0x1800, 16))
            else:
                return decode_string(context.emulator.read_bytes(unpack_uint32(read_symbol("namingScreenDataPtr")) + 0x11, 16))
        except Exception:
            return None
        
    @property
    def cur_page(self) -> int:
        try:
            if context.rom.game_title not in ["POKEMON RUBY", "POKEMON SAPP"]:
                return [1,2,0].index(context.emulator.read_bytes(unpack_uint32(read_symbol("sNamingScreen")) + 0x1E22, 1)[0])
            else:
                return [0x3c,0x42,0x3F].index(context.emulator.read_bytes(0x03001858, 1)[0])
        except Exception:
            return None
    
    @property
    def cur_pos(self) -> tuple:
        x_val = None
        y_val = None
        if context.rom.game_title not in ["POKEMON RUBY", "POKEMON SAPP"]:
            x_val = int(context.emulator.read_bytes(0x03007D98, 1)[0])
            if context.rom.game_title == "POKEMON EMER":
                y_val = int(context.emulator.read_bytes(0x030023A8, 1)[0]/16)-5
            else:
                y_val = int(context.emulator.read_bytes(0x030031D8, 1)[0]/16)-5
        else:
            try:
                if self.cur_page == 2:
                    x_val = [0x1B,0x33,0x4B,0x63,0x7B,0x93,0xBC].index(context.emulator.read_bytes(0x0300185E, 1)[0])
                else:
                    x_val = [0x1B,0x2B,0x3B,0x53,0x63,0x73,0x83,0x9B,0xBC].index(context.emulator.read_bytes(0x0300185E, 1)[0])
            except Exception:
                pass
            y_val = int(context.emulator.read_bytes(0x0300185C, 1)[0]/16)-4
        return (x_val, y_val)

def get_keyboard():
    return Keyboard()

# Currently need to send max length of name if naming a pokemon
# Max length for boxes is 8 and max length for pokemon name is 10
def type_name(name : str, max_length = 8 : int):
    if len(name) > max_length:
        name = name[:max_length]
    name = ''.join([char if char in valid_characters else " " for char in name])
    goto = [0,0,0]
    for page in range(len(key_layout[lang])):
        for num, row  in enumerate(key_layout[lang][page]["array"]):
            if name[0] in row:
                goto = [row.index(name[0]), num, page]
                break
    cur_char = 0
    press = None
    last_pos = None
    h = key_layout[lang][0]["height"]
    w = key_layout[lang][0]["width"]
    done = False
    keyboard = get_keyboard()
    while (keyboard.cur_pos[0] > w and keyboard.cur_pos[1] > h) or len(keyboard.text_buffer) > 0:
        keyboard = get_keyboard()
        context.emulator.press_button("B")
        context.emulator.run_single_frame()
    while True and context.bot_mode != "Manual":
        keyboard = get_keyboard()
        page = keyboard.cur_page
        if page <= 3:
            if h != key_layout[lang][page]["height"] or w != key_layout[lang][page]["width"]:
                h = key_layout[lang][page]["height"]
                w = key_layout[lang][page]["width"]
            spot = keyboard.cur_pos
            if spot == last_pos or (last_pos is None and spot[0] <= w and spot[1] <= h):
                if page != goto[2]: # Press Select until on correct page
                    while page != goto[2]:
                        context.emulator.press_button("Select")
                        context.emulator.run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)
                        page = get_keyboard().cur_page
                    last_pos = None
                elif spot[0] == goto[0] and spot[1] == goto[1]: # Press A if on correct character
                    last_pos = spot
                    while len(get_keyboard().text_buffer) < cur_char + 1:
                        context.emulator.press_button("A")
                        context.emulator.run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)
                    cur_char += 1
                    if len(get_keyboard().text_buffer) >= len(name):
                        break
                    else:
                        found = False
                        for num, row in enumerate(key_layout[lang][page]["array"]):
                            if name[cur_char] in row:
                                goto = [row.index(name[cur_char]), num, page]
                                found = True
                                break
                        if not found:
                            for page_num, new_page in enumerate(key_layout[lang]):
                                for num, row in enumerate(new_page["array"]):
                                    if name[cur_char] in row:
                                        goto = [row.index(name[cur_char]), num, page_num]
                                        found = True
                                        break
                                if found:
                                    break   
                else:
                    if spot[0] < goto[0]:
                        press = "Right"
                    elif spot[0] > goto[0]:
                        press = "Left"
                    elif (spot[1] < goto[1] or (spot[1] == h - 1 and goto[1] == 0)) and not (spot[1] == 0 and goto[1] == h-1):
                        press = "Down"
                    else:
                        press = "Up"
                    context.emulator.press_button(press)
                    context.emulator.run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)
                    last_pos = None
            else:
                context.emulator.run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)
        else:
            context.emulator.run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)
    context.emulator.release_button("A")
    context.emulator.release_button("Down")
    context.emulator.release_button("Up")
    context.emulator.release_button("Left")
    context.emulator.release_button("Right")
    context.emulator.release_button("Start")
    context.emulator.release_button("Select")
    context.emulator.run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)
    while get_keyboard().enabled:
        keyboard = get_keyboard()
        if keyboard.cur_pos[0] > w or (keyboard.cur_pos == (8,0) and context.rom.game_title in ["POKEMON RUBY", "POKEMON SAPP"]):
            context.emulator.press_button("A")
            context.emulator.run_single_frame()
        else:
            context.emulator.press_button("Start")
            context.emulator.run_single_frame()
    
