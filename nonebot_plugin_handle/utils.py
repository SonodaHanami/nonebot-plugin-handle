import json
import random
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import ImageFont
from PIL.Image import Image as IMG
from PIL.ImageFont import FreeTypeFont
from pypinyin import Style, pinyin

resource_dir = Path(__file__).parent / "resources"
fonts_dir = resource_dir / "fonts"
data_dir = resource_dir / "data"
idiom_path = data_dir / "idioms.txt"
answer_path = data_dir / "answers.json"

min_category_cnt = 3
max_category_cnt = 5

game_mode = {
    'handle': {
        'name': '成语',
        'answer_path': data_dir / "answers.json"
    },
    'arkdle': {
        'name': '舟语',
        'answer_path': data_dir / "answers_arknights.json"
    },
    'dordle': {
        'name': '刀语',
        'answer_path': data_dir / "answers_dota2.json"
    }
}

def init_answers():
    reply = ['正在初始化词库']
    for mode in game_mode:
        with game_mode[mode]['answer_path'].open("r", encoding="utf-8") as f:
            answers = json.load(f)
            game_mode[mode]['answers'] = answers
            game_mode[mode]['word_to_pinyin'] = {}
            for answer in game_mode[mode]['answers']:
                game_mode[mode]['word_to_pinyin'][answer['word']] = [[py] for py in answer.get("pinyin", [])]
            reply.append('加载了{}个{}'.format(len(game_mode[mode]['answers']), game_mode[mode]['name']))
    return '\n'.join(reply)

def legal_idiom(word: str, mode: str) -> bool:
    return word in game_mode[mode]['word_to_pinyin'].keys()

def random_idiom(mode, custom_category: List = []) -> Tuple[str, str, str, list, list]:
    answers = game_mode[mode]['answers']
    all_categories = set()
    for answer in answers:
        for category in answer.get("category", []):
            all_categories.add(category)
    enabled_category_cnt = min(random.randint(min_category_cnt, max_category_cnt), len(all_categories))
    selected_category = random.sample(custom_category or all_categories, enabled_category_cnt)
    selected_answers = []
    if selected_category:
        for answer in answers:
            for category in answer.get("category", []):
                if category in selected_category:
                    selected_answers.append(answer)
                    break
        answer = random.choice(list(selected_answers))
        # print(selected_category, answer)
    else:
        answer = random.choice(answers)
    return (mode, answer["word"], answer["explanation"], answer.get("category", []), selected_category)


# fmt: off
# 声母
INITIALS = [
    "zh", "z", "y", "x", "w", "t", "sh", "s", "r", "q", "p",
    "n", "m", "l", "k", "j", "h", "g", "f", "d", "ch", "c", "b"
    ]
# 韵母
FINALS = [
    "ün", "üe", "üan", "ü", "uo", "un", "ui", "ue", "uang",
    "uan", "uai", "ua", "ou", "iu", "iong", "ong", "io", "ing",
    "in", "ie", "iao", "iang", "ian", "ia", "er", "eng", "en",
    "ei", "ao", "ang", "an", "ai", "u", "o", "i", "e", "a"
]
# fmt: on


def get_pinyin(idiom: str, default_pinyin: list = []) -> List[Tuple[str, str, str]]:
    pys = default_pinyin or pinyin(idiom, style=Style.TONE3, v_to_u=True)
    results = []
    for p in pys:
        py = p[0]
        if py[-1].isdigit():
            tone = py[-1]
            py = py[:-1]
        else:
            tone = ""
        initial = ""
        for i in INITIALS:
            if py.startswith(i):
                initial = i
                break
        final = ""
        for f in FINALS:
            if py.endswith(f):
                final = f
                break
        results.append((initial, final, tone))  # 声母，韵母，声调
    return results

def query_word(name: str, word: str) -> str:
    for mode in game_mode:
        if name == game_mode[mode]['name']:
            for ans in game_mode[mode]['answers']:
                if word == ans['word']:
                    return '【{}】\n拼音：{}\n所属范围：{}\n释义：{}'.format(
                        word,
                        ' '.join(ans.get('pinyin', [py[0] for py in pinyin(word, style=Style.TONE3, v_to_u=True)])),
                        '、'.join(ans.get('category', [])),
                        ans['explanation'].replace('；', '\n')
                    )


def save_jpg(frame: IMG) -> BytesIO:
    output = BytesIO()
    frame = frame.convert("RGB")
    frame.save(output, format="jpeg")
    return output


def load_font(name: str, fontsize: int) -> FreeTypeFont:
    return ImageFont.truetype(str(fonts_dir / name), fontsize, encoding="utf-8")
