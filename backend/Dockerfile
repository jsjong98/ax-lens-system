FROM python:3.12-slim

WORKDIR /app

# 시스템 의존성 + Playwright용 브라우저 의존성
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 libatspi2.0-0 libwayland-client0 \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright Chromium 설치
RUN playwright install chromium

# 소스 복사
COPY . .

# uploads, results, persist 디렉토리 생성 (root로 실행하므로 권한 문제 없음)
RUN mkdir -p uploads results /app/persist

# Railway가 PORT 환경변수를 주입함
ENV PORT=8000

EXPOSE ${PORT}

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
