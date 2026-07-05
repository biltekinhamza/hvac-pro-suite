# Whatsapp Havalandirma Bot

FastAPI tabanli web siparis, WhatsApp bot ve Parasut teklif entegrasyonu projesi.

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
docker compose up --build
```

Adres: http://127.0.0.1:8010

Webhook endpointleri:

- GET/POST `/webhook`
- GET/POST `/webhook/whatsapp`

Meta Callback URL icin onerilen adres:

```text
https://PUBLIC_ADRES/webhook/whatsapp
```
