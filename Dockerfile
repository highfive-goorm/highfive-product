# 1. 공식 Python 이미지 사용
FROM python:3.12

# 1-1. 타임존 설정 (tzdata 설치 + Asia/Seoul로 링크)
RUN apt-get update && apt-get install -y tzdata \
  && ln -snf /usr/share/zoneinfo/Asia/Seoul /etc/localtime \
  && echo "Asia/Seoul" > /etc/timezone \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 의존성 설치
COPY requirements.txt .
RUN pip install -r requirements.txt

# 4. 전체 앱 복사
COPY . /app

# 5. FastAPI 실행 (main.py 안에 app 인스턴스가 있어야 함)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
