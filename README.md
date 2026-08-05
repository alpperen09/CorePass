# CorePass

Yerel (local-first) çalışan, açık kaynaklı bir şifre/hesap kasası yöneticisi.
Veriler diskte yalnızca **AES tabanlı Fernet şifrelemesiyle** saklanır; master
parolanız hiçbir zaman düz metin olarak diske yazılmaz veya ağa gönderilmez.

## Hızlı Başlangıç (Geliştirme Ortamı)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd app
python main.py
```

İlk açılışta master parolanızı belirlersiniz; bu andan itibaren kasa
`~/.corepass/vault.enc` içinde şifreli olarak tutulur.

## Otomatik Doldurma Özellikleri

CorePass eklentisi artık diğer şifre yöneticileri (Bitwarden, Proton Pass vb.)
gibi tam otomatik doldurma desteği sunar:

- **Satır içi ikon:** Şifre alanlarının içine otomatik olarak 🔒 ikonu yerleştirilir; tıklanınca o site için kayıtlı hesaplar açılır listede gösterilir.
- **Tek tıkla doldurma:** Listeden bir hesap seçildiğinde kullanıcı adı ve şifre alanları otomatik doldurulur (React/Vue gibi framework'lerin state'ini de günceller).
- **Popup'ta "Bu site için" bölümü:** Eklenti popup'ı açıldığında, o an ziyaret edilen siteyle eşleşen hesaplar en üstte ayrı gösterilir ve doğrudan "Doldur" butonuyla forma yazılabilir.
- **Yeni hesap kaydetme önerisi:** Bir giriş formu gönderildiğinde ve kasada eşleşen kayıt yoksa, sayfa üzerinde "Bu hesabı kaydetmek ister misiniz?" banner'ı belirir.
- **Sağ tık menüsü:** Herhangi bir düzenlenebilir alanda sağ tıklayıp "CorePass ile doldur" seçilebilir.
- **Klavye kısayolu:** `Ctrl+Shift+L` (Mac: `Cmd+Shift+L`) ile aktif sekmedeki en uygun eşleşme otomatik doldurulur.
- **SPA desteği:** `MutationObserver` ile dinamik olarak DOM'a eklenen formlar da (React/Vue tabanlı siteler) otomatik algılanır.

Tüm otomatik doldurma arayüzü (açılır liste, kayıt banner'ı) **Shadow DOM**
içinde izole çalışır; ziyaret edilen sitenin CSS'i CorePass arayüzünü
bozamaz ve tam tersi de geçerlidir.

## Chrome Eklentisini Yükleme

1. Chrome'da `chrome://extensions` adresine gidin.
2. Sağ üstten **Geliştirici modu**'nu açın.
3. **Paketlenmemiş öğe yükle**'ye tıklayıp `extension/` klasörünü seçin.
4. CorePass masaüstü uygulamasını açın, kasanızın kilidini açın; üst barda
   görünen **8 haneli eşleştirme kodunu** eklenti popup'ına girin.

## PyInstaller ile .exe Derleme

```bash
pip install pyinstaller
pyinstaller build/CorePass.spec
```

Derlenen dosya `dist/CorePass.exe` konumunda oluşur. Tek dosyalık çıktı
isterseniz spec dosyasındaki `EXE` bloğuna `--onefile` mantığı eklemek yerine
şu komutu doğrudan kullanabilirsiniz:

```bash
pyinstaller --name CorePass --windowed --onefile app/main.py
```

## Docker ile Çalıştırma (API + Şifreleme Çekirdeği)

```bash
docker build -t corepass .
docker run -p 5732:5732 -v corepass_data:/root/.corepass corepass
```

> GUI, konteyner içinde varsayılan olarak çalışmaz (display gerektirir).
> Docker imajı; API'yi, şifreleme mantığını ve kasa yönetimini izole bir
> ortamda test etmeniz için hazırlanmıştır.

## Güvenlik Notları

- Local API sadece `127.0.0.1:5732` üzerinde dinler, dış ağdan erişilemez.
- Eklenti ile API arasındaki her istek `X-CorePass-Token` header'ı ile
  doğrulanır; token, uygulama her açıldığında yeniden üretilir.
- Master parola PBKDF2HMAC-SHA256 (480.000 iterasyon) ile anahtara
  dönüştürülür; anahtar diske hiçbir zaman yazılmaz.
- `.gitignore`, kasa dosyalarının (`vault.enc`, `vault_salt.bin`) yanlışlıkla
  repoya eklenmesini engeller.

## Proje Yapısı

```
CorePass/
├── app/            # Python backend + CustomTkinter GUI
├── extension/      # Chrome eklentisi (Manifest V3)
├── build/          # PyInstaller .spec dosyası
├── requirements.txt
├── Dockerfile
└── .gitignore
```
