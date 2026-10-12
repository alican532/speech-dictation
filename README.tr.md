# Speech Dictation

[English](README.md)

Masaüstü için dikte ve çeviri. Bir kısayola ya da yüzen butona basın, konuşun; metin yazdığınız yere yapıştırılır.

İki servis hazır gelir:

| Servis | Dikte | Çeviri |
|---|---|---|
| **Groq** (varsayılan) | Whisper Large v3 ya da Large v3 Turbo | Whisper yazıya döker, GPT-OSS 120B ya da 20B çevirir |
| **Gemini** | Gemini 3.5 Transcribe Live, konuşurken canlı | Gemini 3.5 Live Translate |

İkisi de listedeki her dile çevirir. Seçtiğiniz servisin tek bir API anahtarı yeterlidir.

## Özellikler

- **Yüzen buton.** Windows'un sesle yazma çubuğu (Win+H) gibi her zaman üstte duran küçük bir çubuk. Odağı hiç almaz, bu yüzden metin yazdığınız pencereye gider. Butonların dışındaki herhangi bir yerinden tutup sürükleyebilirsiniz; bıraktığınız yeri hatırlar.
  - **Mikrofon:** dikteyi başlatır ya da durdurur.
  - **Mikrofonun köşesindeki dil rozeti** (örneğin `EN`): o dile çeviriyi başlatır ya da durdurur. Çeviri sırasında maviye döner.
  - **Kilit:** siz durdurana kadar duraklamalarda da dinlemeye devam eder.
  - **✕:** çubuğu gizler (süren bir kayıt varsa iptal eder). Bir sonraki dikte onu geri getirir.
- **Otomatik durdurma.** Birkaç saniye sessiz kalınca kayıt biter ve metin yapıştırılır; son saniyeleri bir halka geri sayar. Hiç konuşulmazsa kayıt atılır ve hiçbir şey gönderilmez.
- **Sesler.** Windows'ta, Windows sesle yazmanın başlama, bitiş ve iptal sesleri; macOS ve Linux'ta uygulamanın `assets/sounds` içindeki kendi sesleri.
- **Duraklama kesme (Groq).** Cümlelerin önündeki, arkasındaki ve aralarındaki sessizlik gönderilmeden kesilir. Bu hem hızlandırır hem de Whisper'ın sessizlikte metin uydurmasını önler; "Altyazı M.K." gibi bilinen hayalet cümleler de atılır.
- **Akıllı düzeltme (Groq).** Metin modeli, Whisper'ın yanlış duyduğu kelimeleri cümlenin bütününe bakarak düzeltir ve gerisine dokunmaz. Cevabı yeniden yazılmış gibi görünürse ya da istek başarısız olursa Whisper'ın metni olduğu gibi yapıştırılır.
- **Sözlük (Groq).** Sık kullandığınız isimler ve terimler, örneğin `Claude`. Whisper'a yazım ipucu olarak ve metin modeline gider.
- **İki arayüz dili:** İngilizce ve Türkçe. Siz seçene kadar sistem dilini kullanır.
- **Oturum açılınca başlat**, Ayarlar'da bir seçenek (Windows'ta Run kaydı, macOS'ta LaunchAgent, Linux'ta autostart dosyası).

## Gereksinimler

- Windows 10 ya da 11, macOS ya da Linux (bkz. [macOS ve Linux](#macos-ve-linux); şimdiye kadar yalnızca Windows'ta test edildi)
- Kaynaktan çalıştırmak için Python 3.11 ya da üstü
- Kullandığınız servisin API anahtarı:
  - Groq: [console.groq.com/keys](https://console.groq.com/keys)
  - Gemini: [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

## Kaynaktan çalıştırma

```powershell
git clone https://github.com/alican532/speech-dictation.git
cd speech-dictation
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\pythonw launch.py
```

İlk açılışta Ayarlar penceresi açılır ve anahtar ister. Sonrasında Ayarlar'a ve Çıkış'a tepsi simgesine sağ tıklayarak ulaşırsınız.

Masaüstü kısayolu, hedefi `.venv\Scripts\pythonw.exe`, argümanı `launch.py`, çalışma klasörü repo olacak şekilde oluşturulabilir.

## Kısayollar

| İşlem | Varsayılan |
|---|---|
| Dikte | `Alt+Z` |
| Çeviri | yok, Ayarlar'dan seçin |
| İptal | `Esc` |

Başlatmak için kısayola bir kez, durdurmak için bir kez daha basın. Tepsi simgesine tıklamak dikte kısayoluyla aynı işi yapar. Ayarlar penceresi öndeyken dikte başlamaz, böylece metin onun alanlarından birine yapıştırılmaz; önce yazacağınız pencereye tıklayın.

## macOS ve Linux

Her özellik üç sistemde de çalışacak şekilde yazıldı. Farklı olanlar:

**macOS**
- Sorulduğunda Sistem Ayarları › Gizlilik ve Güvenlik'te üç izni verin: *Mikrofon* (dinlemek için), *Erişilebilirlik* (Cmd+V ile yapıştırmak için) ve *Girdi İzleme* (genel kısayollar için).
- Derlenmiş uygulama bir menü çubuğu uygulamasıdır, Dock'ta simgesi olmaz.
- Yüzen buton etkinleştirmeyen bir paneldir; ona tıklamak yazdığınız uygulamayı önde bırakır. Her masaüstünde ve tam ekran uygulamaların üstünde görünür.

**Linux**
- X11: her şey Windows'taki gibi çalışır.
- KDE Plasma ya da Hyprland üzerinde Wayland: uygulama, pencere yöneticisinden butonu üstte, görev çubuğunun dışında ve odaksız tutmasını ister. Sürükleme pencere yöneticisine devredildiği için butonun yeri açılışlar arasında hatırlanmaz; ekranın alt ortasına yakın başlar.
- GNOME ve diğer masaüstlerinde Wayland: bunlar bir pencereyi odaksız ya da üstte tutmanın bir yolunu sunmaz. Kısayollar her zamanki gibi çalışır. Butona tıklayarak başlatılan bir dikte metni kopyalar ve Ctrl+V'ye basmanızı ister, çünkü tıklama odağı butona taşımıştır.
- Wayland'da yapıştırma sırasıyla `/dev/uinput`, `ydotool` / `wtype` ya da masaüstünün uzaktan giriş izni üzerinden yapılır.

## Ayarlar

Sadece seçili servisin bölümü görünür.

| Bölüm | Ayarlar |
|---|---|
| Servis | Groq Whisper Large v3, Groq Whisper Large v3 Turbo, Gemini Live |
| Groq | Anahtar, konuştuğunuz dil, metin modeli, sözlük, akıllı düzeltme, duraklama kesme |
| Gemini | Anahtar |
| Genel | Uygulama dili, dikte / çeviri / iptal kısayolları, çeviri dili, otomatik durdurma, sesler, oturum açılınca başlat |

Ayarların saklandığı yer:

| Sistem | Dosya |
|---|---|
| Windows | `%APPDATA%\SpeechDictation\config.json` |
| macOS | `~/Library/Application Support/SpeechDictation/config.json` |
| Linux | `${XDG_CONFIG_HOME:-~/.config}/SpeechDictation/config.json` |

İlk açılışta, orijinal GeminiSpeechAPI uygulamasından kalan bir ayar dosyası varsa bir kez kopyalanır.

## Maliyet ve gizlilik

- **Groq:** Whisper Large v3 ses saati başına yaklaşık $0,111, Turbo yaklaşık $0,04; her istek en az 10 saniye üzerinden ücretlendirilir. GPT-OSS metin istekleri bir sentin çok küçük bir kısmı tutar. Kullanım sınırlı ücretsiz katman vardır.
- **Gemini:** Ücretsiz katmanda ücret yoktur; bu katmanda Google içeriği ürünlerini geliştirmek için kullanabilir. Ücretli katmanda dikte dakikası yaklaşık $0,009, çeviri dakikası yaklaşık $0,037'dir.

Güncel rakamlar için sağlayıcıların fiyat sayfalarına bakın. Ses yalnızca seçtiğiniz servise gider; uygulamanın kendine ait bir sunucusu yoktur.

## Kurulum dosyası oluşturma

```powershell
.venv\Scripts\python -m pip install pyinstaller
.venv\Scripts\python packaging\build.py
```

Windows'ta ayrıca [Inno Setup 6](https://jrsoftware.org/isinfo.php) gerekir. Sonuç, kullanıcı başına kurulan `dist\SpeechDictation-Setup.exe` dosyasıdır. macOS'ta `dist/SpeechDictation-macos.dmg`, Linux'ta `./SpeechDictation/install.sh` ile kurulan `dist/SpeechDictation-linux.tar.gz` oluşur. GitHub'da bir sürüm (release) yayınlamak, aynı derlemeyi `.github/workflows/release.yml` ile Windows, macOS ve Linux için çalıştırır.

Kurulu bir sürüm, açıldıktan birkaç saniye sonra ve altı saatte bir bu reponun son sürümüne bakar ve kendini günceller. Kaynaktan çalışan kopya kendini hiç güncellemez. Repo gizli olduğu sürece GitHub bu kontrole anahtarsız cevap vermez, bu yüzden kurulu sürümler kendi sürümlerinde kalır.

## Kaynak

Bu proje [ruwiss/gemini_speech](https://github.com/ruwiss/gemini_speech) reposunun bir kopyası olarak başladı ve 2.0.0 sürümünden itibaren kendi yolunda ilerliyor. O reponun lisansı olmadığı için bu repo gizli tutuluyor.
