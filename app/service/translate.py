import hashlib
import time
from urllib.parse import urlencode

YOUDAO_SECRET = "U3uACNRWSDWdcsKm"
YOUDAO_WORD_BASE_URL = "https://dict.youdao.com/dictvoice"
YOUDAO_SENTENCE_BASE_URL = "https://dict.youdao.com/pronounce/base"

"""
构建句子的音频-by有道发音
"""
def build_youdao_sentence_voice_url(*, text: str, rate: int = 4, lang: str = "eng", voice_type: str = "2") -> str:
    mystic_time = int(time.time() * 1000)
    params: dict[str, str | int] = {
        "product": "webdict",
        "appVersion": 1,
        "client": "web",
        "mid": 1,
        "vendor": "web",
        "screen": 1,
        "model": 1,
        "imei": 1,
        "network": "wifi",
        "keyfrom": "dick",
        "keyid": "voiceDictWeb",
        "yduuid": "abcdefg",
        "le": lang,
        "phonetic": "",
        "rate": rate,
        "mysticTime": mystic_time,
        "word": text,
        "type": voice_type,
        "id": "",
    }

    point_params = sorted(key for key in params.keys() if key not in {"id", "phonetic"})
    sign_original = "&".join(f"{key}={params[key]}" for key in point_params) + f"&key={YOUDAO_SECRET}"
    params["pointParam"] = ",".join(point_params + ["key"])
    params["sign"] = hashlib.md5(sign_original.encode("utf-8")).hexdigest()
    return f"{YOUDAO_SENTENCE_BASE_URL}?{urlencode(params)}"

"""
构建单词的音频-by有道发音
"""
def build_youdao_word_voice_url(*, text: str) -> str:
    return f"{YOUDAO_WORD_BASE_URL}?audio={text}&type=2"
