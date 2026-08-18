# HVAC Pro Suite

FastAPI tabanli web siparis ve Parasut teklif entegrasyonu projesi.

- Repo: `https://github.com/biltekinhamza/hvac-pro-suite` (gizli)

## Calistirma

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8010
```

Adres: http://127.0.0.1:8010

`--host 0.0.0.0` sayesinde uygulama ayni agdaki diger PC'lerden de erisilebilir.

## Ilk Kapsam

- Musteri siparis ekrani
- Parca listesini API ile dondurme
- SQLite veritabani baslangici
- Havalandirma hesaplama motoru icin modul yapisi

Gizli bilgiler `.env` dosyasinda tutulmalidir. `.env.example` sadece sablondur.


## Docker ile calistirma

```bash
copy .env.example .env
docker compose up --build -d
```

Adres: http://127.0.0.1:8010

Compose proje adi `hvac_pro_suite` olarak sabitlenmistir; komutlari bu
klasorden calistirin. Cloudflare quick tunnel her yeniden olusturuldugunda
yeni bir adres uretebilir ve kalici yayin icin uygun degildir. Kalici yayin
icin named tunnel + alan adi gereklidir (bkz. README'nin sonundaki
"Bulut yayin" bolumu).

## Bulut yayin (Oracle + Cloudflare Tunnel)

Sunucuda (Ubuntu) projeyi klonlayip Docker ile ayaga kaldirin:

```bash
git clone https://github.com/biltekinhamza/hvac-pro-suite.git hvac
cd hvac
cp .env.example .env        # .env degerlerini doldurun
docker compose up -d --build
```

- Uygulama `0.0.0.0:8010` uzerinde calisir; `docker compose logs tunnel`
  ile Cloudflare quick tunnel adresi bulunur ve `PUBLIC_BASE_URL` olarak
  `.env` icerisine yazilir.
- Veriler kalici olarak `./data` dizininde saklanir (volume baglantisi).
- Android APK dosyasi (`android-client/.../app-debug.apk`) sunucuya
  yuklenerek `/app/downloads/hvac-mobile.apk` olarak baglanmalidir; aksi
  halde mobil indirme sayfasi 404 verir.
- Mobil uygulamanin release surumu yalniz HTTPS kabul eder; bu yuzden
  yayin Cloudflare Tunnel uzerinden yapilmalidir.

## Ayni agdaki PC'lerden siparis sayfasina erisim

1. Uygulama `0.0.0.0:8010` uzerinde calismali (Docker compose zaten bunu yapar).
2. Sunucunun ag IP'sini bulun: `ipconfig` komutunda `IPv4 Address` (ornek: `192.168.1.101`).
3. Diger PC'ler tarayicidan `http://<IP>:8010` adresine girsin (ornek: `http://192.168.1.101:8010`).
4. Ilk kez erisilemiyorsa Windows Guvenlik Duvari'nin 8010 numarali portuna gelen baglantilara izin verin:

```powershell
New-NetFirewallRule -DisplayName "HVAC Pro Suite (8010)" -Direction Inbound -Protocol TCP -LocalPort 8010 -Action Allow -Profile Any
```
