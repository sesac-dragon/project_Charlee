# 1. 베이스 이미지 설정
FROM python:3.10-slim

# 2. 작업 디렉터리 설정
WORKDIR /usr/src/app

# 3. 시스템 패키지 업데이트 및 git 설치 (GitPython 종속성)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# 4. requirements.txt 복사 및 종속성 설치
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 5. 프로젝트 전체 소스 코드 복사
COPY . .

# 6. 애플리케이션 실행
ENV PYTHONPATH="/usr/src/app"
CMD ["python", "core/main.py"]
