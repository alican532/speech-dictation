"""Interface languages.

English text is the key, so English needs no table and any string that is
missing from a table simply shows in English. To add a language, add it to
LANGUAGES and give it a table in TABLES.
"""

LANGUAGES = (
    ("English", "en"),
    ("Türkçe", "tr"),
)

TR = {
    # Tray
    "Settings": "Ayarlar",
    "Quit": "Çıkış",
    "Speech Dictation is ready": "Speech Dictation hazır",
    "Speech Dictation: add an API key": "Speech Dictation: API anahtarı ekleyin",
    "Downloading version %s": "%s sürümü indiriliyor",
    "Version %s is ready to install": "%s sürümü kurulmaya hazır",
    "Installing version %s, the app will restart": "%s sürümü kuruluyor, uygulama yeniden başlayacak",
    "Update failed": "Güncelleme başarısız",

    # Floating button
    "Stop": "Durdur",
    "Start dictation": "Dikteyi başlat",
    "Translate into %s": "%s diline çevir",
    "Keep listening until I stop": "Ben durdurana kadar dinle",
    "Locked: auto-stop is off": "Kilitli: otomatik durdurma kapalı",
    "Hide until the next dictation": "Bir sonraki dikteye kadar gizle",

    # Settings
    "Service": "Servis",
    "Groq key": "Groq anahtarı",
    "I speak": "Konuştuğum dil",
    "Text model": "Metin modeli",
    "Vocabulary": "Sözlük",
    "Gemini key": "Gemini anahtarı",
    "General": "Genel",
    "App language": "Uygulama dili",
    "Record": "Kayıt",
    "Translate": "Çeviri",
    "Translate to": "Çeviri dili",
    "Cancel": "İptal",
    "Auto-stop": "Otomatik durdur",
    "Save": "Kaydet",
    "Saved": "Kaydedildi",
    "console.groq.com API key": "console.groq.com API anahtarı",
    "AI Studio API key": "AI Studio API anahtarı",
    "Names and terms, separated by commas": "İsimler ve terimler, virgülle ayırın",
    "Detect automatically": "Otomatik algıla",
    "Smart correction: fix misheard words": "Akıllı düzeltme: yanlış duyulan kelimeleri düzelt",
    "Cut pauses before sending": "Göndermeden önce duraklamaları kes",
    "Play a sound when listening starts and stops": "Dinleme başlayınca ve bitince ses çal",
    "Start with Windows": "Windows ile başlat",
    "Off": "Kapalı",
    "After %d s of silence": "%d sn sessizlikten sonra",
    "recommended": "önerilen",
    "fastest": "en hızlı",
    "Click, then press the keys": "Tıklayın, sonra tuşlara basın",
    "Press the keys": "Tuşlara basın",
    "Whisper writes down what you say. The Text model fixes words it misheard "
    "and does the translating. Vocabulary words are always spelled the way you "
    "write them.":
        "Whisper söylediklerinizi yazıya döker. Metin modeli yanlış duyulan kelimeleri "
        "düzeltir ve çeviriyi yapar. Sözlükteki kelimeler her zaman sizin yazdığınız gibi yazılır.",
    "Gemini Live writes down what you say as you speak, and translates it live.":
        "Gemini Live siz konuşurken söylediklerinizi yazıya döker ve canlı olarak çevirir.",
    "The lock on the floating button keeps it listening through pauses until you stop it.":
        "Yüzen butondaki kilit, siz durdurana kadar duraklamalarda da dinlemeye devam etmesini sağlar.",

    # Language names
    "English": "İngilizce",
    "Turkish": "Türkçe",
    "German": "Almanca",
    "French": "Fransızca",
    "Spanish": "İspanyolca",
    "Italian": "İtalyanca",
    "Portuguese": "Portekizce",
    "Dutch": "Felemenkçe",
    "Polish": "Lehçe",
    "Russian": "Rusça",
    "Ukrainian": "Ukraynaca",
    "Arabic": "Arapça",
    "Chinese": "Çince",
    "Japanese": "Japonca",
    "Korean": "Korece",

    # Messages
    "Add a Gemini API key in Settings": "Ayarlar'dan bir Gemini API anahtarı ekleyin",
    "No speech detected": "Konuşma algılanmadı",
    "Copied. Could not paste": "Kopyalandı ama yapıştırılamadı",
    "Recording is too short": "Kayıt çok kısa",
    "Live transcription stops at 10 minutes": "Kayıt en fazla 10 dakika sürebilir",
    "No microphone": "Mikrofon bulunamadı",
    "Microphone did not open": "Mikrofon açılamadı",
    "Transcription failed": "Yazıya dökme başarısız",
    "Add a Groq API key in Settings": "Ayarlar'dan bir Groq API anahtarı ekleyin",
    "Groq rejected the API key": "Groq API anahtarını reddetti",
    "Groq limit reached, try again shortly": "Groq kullanım sınırına ulaşıldı, biraz sonra tekrar deneyin",
    "Could not reach Groq": "Groq'a ulaşılamadı",
    "Translate needs a Gemini API key": "Çeviri için Gemini API anahtarı gerekir",
    "Translation failed": "Çeviri başarısız",
    "SSL certificate failed — reinstall the Linux build": "SSL sertifikası doğrulanamadı — Linux sürümünü yeniden kurun",
    "Shortcut": "Kısayol",
    "Windows already uses %s.": "%s kısayolunu Windows zaten kullanıyor.",
    "Could not read that shortcut.": "Bu kısayol okunamadı.",
    "Could not read shortcut: %s": "Kısayol okunamadı: %s",
    "Windows would not give %s. Another app holds it.": "%s kısayolu alınamadı, başka bir uygulama kullanıyor.",
    "Record and translate need different shortcuts.": "Kayıt ve çeviri için farklı kısayollar gerekir.",
    "macOS and Linux need pynput (pip install pynput, or reinstall the Linux build)":
        "macOS ve Linux için pynput gerekir (pip install pynput ya da Linux sürümünü yeniden kurun)",
}

TABLES = {"tr": TR}

current = "en"


def tr(text):
    return TABLES.get(current, {}).get(text, text)


def set_language(code):
    global current
    current = code if code in dict((c, n) for n, c in LANGUAGES) else "en"


def system_language():
    from PyQt6.QtCore import QLocale
    code = QLocale.system().name().split("_")[0]
    return code if code in TABLES or code == "en" else "en"
