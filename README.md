# VKV İş Takip API

Masaüstü penceresi yalnız arayüzdür ve bu API'ye bağlanır. Veri katmanı buradadır. Görev, proje, fatura, hatırlatma, rehber, kasa, teklif, talep ve rapor kayıtları bu servisten açılır. Tk arayüzü, e-posta ve PDF üretimi masaüstü programda kalır.

Veri katmanı SQLAlchemy kullanır. Varsayılan veritabanı stage Postgres üzerindeki `stage_vkvdb` (`185.184.210.52:5433`). Şifre `POSTGRES_PASSWORD` ile verilir. Testler `DATABASE_URL` ile SQLite dosyasına bağlanır.

## Çalıştırma

```bash
cd ~/Desktop/is-merkezi/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export API_TOKEN=degistir
export POSTGRES_PASSWORD=...
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Belgeler: http://127.0.0.1:8000/docs

İstek başlığı: `Authorization: Bearer degistir`

Kayıtları bir hesaba bağlamak için isteğe bağlı başlık: `X-Owner-Id: 1`

## Yayın

`API_TOKEN` olmadan korumalı endpoint açılmaz. Docker imajı 8000 portunu dinler. Coolify'da `API_TOKEN` ve `POSTGRES_PASSWORD` verilir. Veritabanı yoksa uygulama açılışta `stage_vkvdb` oluşturup tabloları kurar.

```bash
docker build -t is-merkezi-api .
docker run --rm -p 8000:8000 -e API_TOKEN=degistir -e POSTGRES_PASSWORD=... is-merkezi-api
```
