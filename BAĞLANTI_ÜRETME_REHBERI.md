# Bağlantı Üretme Rehberi

Bu belge, projenin sunucusunu başlattıktan sonra halka açık bir bağlantı üretmek için izlenmesi gereken adımları açıklar.

## 1. Projeyi açın

Terminalde proje klasörüne gidin:

```powershell
cd "c:\Users\TavSan\Desktop\HVAC Pro Suite"
```

## 2. Sanal ortamı etkinleştirin

```powershell
.\.venv\Scripts\Activate.ps1
```

## 3. Uygulamayı başlatın

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Bu komut çalıştığında uygulama şu adreste hizmet vermeye başlar:

```text
http://127.0.0.1:8000
```

## 4. Halka açık bağlantı üretin

Aynı terminalde yeni bir terminal açın ve şu komutu çalıştırın:

```powershell
cloudflared tunnel --url http://127.0.0.1:8000
```

Komut çalıştıktan sonra terminalde bir link üretilecektir. Örnek format:

```text
https://something-trycloudflare.com
```

## 5. Üretilen linki kullanın

Üretilen bağlantı ile proje erişilebilir hale gelir. Örneğin:

```text
https://something-trycloudflare.com/
```

## 6. Sorun yaşanırsa kontrol edin

- Uygulama 8000 portunda çalışıyor mu?
- `uvicorn` komutu başarıyla başladı mı?
- `cloudflared` kurulu mu?
- Firewall / güvenlik duvarı engelleme yapmıyor mu?

## 7. Hızlı özet

```powershell
cd "c:\Users\TavSan\Desktop\HVAC Pro Suite"
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Ardından yeni terminalde:

```powershell
cloudflared tunnel --url http://127.0.0.1:8000
```

## 8. Not

Bu yöntem kısa süreli paylaşım ve test amaçlıdır. Kalıcı kullanım için özel tunnel veya sunucu yapılandırması önerilir.
