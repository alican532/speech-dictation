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
    "Usage": "Kullanım",
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
    "Cut pauses before sending": "Göndermeden önce duraklamaları kes",
    "Play a sound when listening starts and stops": "Dinleme başlayınca ve bitince ses çal",
    "Start with Windows": "Windows ile başlat",
    "Start at login": "Oturum açılınca başlat",
    "Off": "Kapalı",
    "After %d s of silence": "%d sn sessizlikten sonra",
    "recommended": "önerilen",
    "fastest": "en hızlı",
    "Click, then press the keys": "Tıklayın, sonra tuşlara basın",
    "Press the keys": "Tuşlara basın",
    "Whisper writes down what you say once you stop. Vocabulary words are spelled the way you write them.":
        "Whisper siz durunca söylediklerinizi yazıya döker. Sözlükteki kelimeler sizin yazdığınız gibi yazılır.",
    "Scribe writes down what you say once you stop. Vocabulary words are listened for and spelled the way you write them.":
        "Scribe siz durunca söylediklerinizi yazıya döker. Sözlükteki kelimelere özellikle kulak verir "
        "ve onları sizin yazdığınız gibi yazar.",
    "Scribe writes down what you say while you speak, so the text is ready soon after you stop. Vocabulary words are listened for. ElevenLabs edit needs Scribe v2.":
        "Scribe siz konuşurken yazıya döker, bu yüzden metin siz durur durmaz hazır olur. "
        "Sözlükteki kelimelere özellikle kulak verir. ElevenLabs düzenleme için Scribe v2 gerekir.",
    "Correction fixes words the speech service misheard. Translation runs when "
    "you use the Translate shortcut or the badge on the button. ElevenLabs edit "
    "adds 30% to the ElevenLabs price; Google Translate only translates.":
        "Düzeltme, konuşma servisinin yanlış duyduğu kelimeleri düzeltir. Çeviri, çeviri "
        "kısayolunu ya da butondaki rozeti kullandığınızda çalışır. ElevenLabs düzenleme "
        "ElevenLabs ücretine %30 ekler; Google Translate yalnızca çeviri yapar.",
    "API keys": "API anahtarları",
    "ElevenLabs key": "ElevenLabs anahtarı",
    "Google key": "Google anahtarı",
    "elevenlabs.io API key": "elevenlabs.io API anahtarı",
    "Google Cloud key with Cloud Translation on": "Cloud Translation açık bir Google Cloud anahtarı",
    "Speech": "Konuşma",
    "Text": "Metin",
    "Correction": "Düzeltme",
    "Translation": "Çeviri motoru",
    "Leave out filler words (um, uh)": "Dolgu kelimelerini çıkar (ıı, şey)",
    "Separate with commas, for example: Claude, Alican, Google Ads":
        "Virgülle ayırın, örneğin: Claude, Alican, Google Ads",
    "Send vocabulary to Scribe as key terms (extra cost)": "Sözlüğü Scribe'a anahtar terim olarak gönder (ek ücretli)",
    "Scribe listens for these words. ElevenLabs adds $0.05 an hour for Scribe v2 and $0.08 for Realtime. Correction gets the words either way.":
        "Scribe bu kelimeleri özellikle dinler. ElevenLabs, Scribe v2 için saatte $0,05, Realtime için $0,08 ekler. Düzeltme kelimeleri her durumda alır.",
    "ElevenLabs edit": "ElevenLabs düzenleme",
    "same request": "aynı istekte",
    "fast": "hızlı",
    "live": "canlı",
    "Gemini Live writes down what you say as you speak, and translates it live.":
        "Gemini Live siz konuşurken söylediklerinizi yazıya döker ve canlı olarak çevirir.",

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
    "Click the window you want to type in first": "Önce yazacağınız pencereye tıklayın",
    "Copied. Press Ctrl+V to paste": "Kopyalandı. Yapıştırmak için Ctrl+V'ye basın",
    "Recording is too short": "Kayıt çok kısa",
    "Live transcription stops at 10 minutes": "Kayıt en fazla 10 dakika sürebilir",
    "No microphone": "Mikrofon bulunamadı",
    "Microphone did not open": "Mikrofon açılamadı",
    "Transcription failed": "Yazıya dökme başarısız",
    "Add a Groq API key in Settings": "Ayarlar'dan bir Groq API anahtarı ekleyin",
    "Groq rejected the API key": "Groq API anahtarını reddetti",
    "Groq limit reached, try again shortly": "Groq kullanım sınırına ulaşıldı, biraz sonra tekrar deneyin",
    "Could not reach Groq": "Groq'a ulaşılamadı",
    "Add an ElevenLabs API key in Settings": "Ayarlar'dan bir ElevenLabs API anahtarı ekleyin",
    "ElevenLabs rejected the API key": "ElevenLabs API anahtarını reddetti",
    "ElevenLabs limit reached, try again shortly": "ElevenLabs kullanım sınırına ulaşıldı, biraz sonra tekrar deneyin",
    "ElevenLabs credits are used up": "ElevenLabs kredisi bitti",
    "Could not reach ElevenLabs": "ElevenLabs'e ulaşılamadı",
    "Gemini rejected the API key": "Gemini API anahtarını reddetti",
    "Gemini limit reached, try again shortly": "Gemini kullanım sınırına ulaşıldı, biraz sonra tekrar deneyin",
    "Could not reach Gemini": "Gemini'ye ulaşılamadı",
    "Add a Google Cloud API key in Settings": "Ayarlar'dan bir Google Cloud API anahtarı ekleyin",
    "Google Translate rejected the API key": "Google Translate API anahtarını reddetti",
    "Google Translate limit reached, try again shortly": "Google Translate kullanım sınırına ulaşıldı, biraz sonra tekrar deneyin",
    "Could not reach Google Translate": "Google Translate'e ulaşılamadı",
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

    # Usage
    "Today": "Bugün",
    "Last 7 days": "Son 7 gün",
    "This month": "Bu ay",
    "Last 30 days": "Son 30 gün",
    "All time": "Tümü",
    "Estimated cost": "Tahmini maliyet",
    "Dictations": "Dikte",
    "Model": "Model",
    "Used for": "Kullanım amacı",
    "Requests": "İstek",
    "Amount": "Miktar",
    "Dictation": "Dikte",
    "Fixing words": "Düzeltme",
    "Translating": "Çeviri",
    "%s s": "%s sn",
    "%s min": "%s dk",
    "%s h": "%s sa",
    "Summary": "Özet",
    "Details": "Detay",
    "Audio sent": "Gönderilen ses",
    "Saved by cutting pauses": "Duraklama kesme kazancı",
    "recorded %s": "kaydedilen %s",
    "%s of silence cut": "%s sessizlik kesildi",
    "%d without text": "%d tanesi metinsiz",
    "%s on unfinished takes": "%s yarım kalan kayıtlara",
    "%s%% of the budget (%s)": "Bütçenin %%%s kadarı (%s)",
    "Average wait": "Ort. bekleme",
    "Double-click a model to see its requests": "İsteklerini görmek için bir modele çift tıklayın",
    "Highest: %s": "En yüksek: %s",
    "No cost in this period": "Bu dönemde maliyet yok",
    "Every request": "Her istek",
    "By dictation": "Dikteye göre",
    "All models": "Tüm modeller",
    "Any status": "Tüm durumlar",
    "Done": "Tamam",
    "Nothing heard": "Ses duyulmadı",
    "Cancelled": "İptal",
    "Failed": "Hata",
    "Export CSV": "CSV olarak dışa aktar",
    "Time": "Zaman",
    "Status": "Durum",
    "Wait": "Bekleme",
    "%d requests": "%d istek",
    "Pick a row to see how its cost was worked out.": "Maliyetin nasıl hesaplandığını görmek için bir satır seçin.",
    "Total: %s": "Toplam: %s",
    "%d dictations, %d requests": "%d dikte, %d istek",
    "Nothing to show.": "Gösterilecek bir şey yok.",
    "(recorded %s)": "(kaydedilen %s)",
    "%s in + %s out tokens": "%s giriş + %s çıkış token",
    "vocabulary %s": "sözlük %s",
    "edit %s": "düzenleme %s",
    "%s in": "%s giriş",
    "%s out": "%s çıkış",
    "/h": "/sa",
    "/min": "/dk",
    "/M": "/M",
    "(at least %s a request)": "(istek başına en az %s)",
    "not billed: the request was refused": "ücretlendirilmez: istek reddedildi",
    "not in the price table": "fiyat tablosunda yok",
    "Monthly budget": "Aylık bütçe",
    "A tray message when this month's estimated cost passes this amount":
        "Bu ayın tahmini maliyeti bu tutarı geçince tepside bir bildirim",
    "The lock on the floating button keeps it listening through pauses until you stop it. "
    "The monthly budget warns you once a month when the estimated cost on the Usage page passes it.":
        "Yüzen butondaki kilit, siz durdurana kadar duraklamalarda da dinlemeye devam etmesini sağlar. "
        "Aylık bütçe, Kullanım sayfasındaki tahmini maliyet onu geçince ayda bir kez uyarır.",
    "This month's estimated cost is %s, past your %s budget. Click to see the usage.":
        "Bu ayın tahmini maliyeti %s, %s bütçenizi geçti. Kullanımı görmek için tıklayın.",
    "%s tokens": "%s token",
    "%s characters": "%s karakter",
    "no price": "fiyat yok",
    "Nothing used in this period yet.": "Bu dönemde henüz kullanım yok.",
    "Estimates at list prices of %s. Free tiers and free monthly allowances are "
    "not taken off, because the app cannot see whether they still apply. "
    "Requests from before this page existed are not counted. The exact bill "
    "is on each provider's page:":
        "%s tarihli liste fiyatlarıyla tahmindir. Ücretsiz katman ve aylık ücretsiz kotalar "
        "düşülmez, çünkü uygulama bunların hâlâ geçerli olup olmadığını göremez. Bu sayfadan "
        "önceki istekler sayılmaz. Kesin tutar her sağlayıcının kendi sayfasındadır:",
    "Clear history": "Geçmişi temizle",
    "Delete the whole usage history on this computer? This cannot be undone.":
        "Bu bilgisayardaki tüm kullanım geçmişi silinsin mi? Geri alınamaz.",
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
