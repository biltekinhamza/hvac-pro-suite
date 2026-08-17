# HVAC Pro Suite

FastAPI tabanli web siparis ve Parasut teklif entegrasyonu projesi.

## Calistirma

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8010
```

Adres: http://127.0.0.1:8010

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
yeni bir adres uretebilir ve kalici yayin icin uygun degildir.
