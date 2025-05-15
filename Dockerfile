# 1. 공식 Python 이미지 사용
FROM python:3.12

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 의존성 설치
COPY requirements.txt .
RUN pip install -r requirements.txt

# 4. 전체 앱 복사
COPY . /app

# 5. FastAPI 실행 (main.py 안에 app 인스턴스가 있어야 함)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

