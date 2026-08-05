# CorePass - Docker Yapılandırması
#
# NOT: CustomTkinter tabanlı GUI, bir konteyner içinde grafik arayüz olmadan
# doğrudan çalıştırılamaz (X11/display gerektirir). Bu Dockerfile, öncelikle
# CorePass'in Flask API + şifreleme/kasa mantığını izole ve tekrarlanabilir
# bir ortamda test etmek/çalıştırmak için tasarlanmıştır.
# GUI'yi de konteynerde görmek isterseniz README'deki X11 forwarding notuna bakın.

FROM python:3.11-slim

# Sistem bağımlılıkları (tkinter için gerekli paylaşımlı kütüphaneler dahil)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-tk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /corepass

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app

ENV PYTHONUNBUFFERED=1
ENV COREPASS_HOME=/root/.corepass

EXPOSE 5732

WORKDIR /corepass/app

# Konteyner içinde varsayılan olarak sadece API + şifreleme çekirdeğini çalıştırır.
# GUI gerekiyorsa CMD'yi "python", "main.py" olarak değiştirip X11 forwarding kurun.
CMD ["python", "-c", "import api; api.run_api_server(); import time; \
print('CorePass API 127.0.0.1:5732 üzerinde çalışıyor (Ctrl+C ile durdurun)'); \
[time.sleep(3600) for _ in iter(int, 1)]"]
