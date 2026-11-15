# VKV İş Takip API

Masaüstü penceresi yalnız arayüzdür ve bu API'ye bağlanır. Veri katmanı buradadır. Görev, proje, fatura, hatırlatma, rehber, kasa, teklif, talep ve rapor kayıtları bu servisten açılır. Tk arayüzü, e-posta ve PDF üretimi masaüstü programda kalır.

Veritabanı, masaüstüyle aynı `is_merkezi.db` şemasını kullanır.

## Çalıştırma

```bash
cd ~/Desktop/is-merkezi-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export API_TOKEN=degistir
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Belgeler: http://127.0.0.1:8000/docs

İstek başlığı: `Authorization: Bearer degistir`

Kayıtları bir hesaba bağlamak için isteğe bağlı başlık: `X-Owner-Id: 1`

Masaüstündeki mevcut veriyi kullanmak için:

```bash
export IS_MERKEZI_HOME="$HOME/Library/Application Support/IsMerkezi"
```

Boş bırakılırsa veriler proje içindeki `data/` klasörüne yazılır. Masaüstü uygulama açıkken aynı dosyaya yazmayın.

## Yayın

`API_TOKEN` olmadan korumalı endpoint açılmaz. Docker imajı 8000 portunu dinler; token ortam değişkeni olarak verilir.

```bash
docker build -t is-merkezi-api .
docker run --rm -p 8000:8000 -e API_TOKEN=degistir -v ismerkezi:/data is-merkezi-api
```
