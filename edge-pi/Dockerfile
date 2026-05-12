# 베이스 이미지: Raspberry Pi 5(ARM64) 호환 및 Camera 3의 libcamera 의존성을 위해 Debian Bookworm 기반 사용
FROM python:3.10-slim-bookworm

# 상호작용 프롬프트 방지
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# 1. 시스템 의존성 설치
# libcamera, gstreamer (Camera Module 3 용)
# build-essential, cmake (추후 패키지 빌드 용)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcamera-dev \
    libcamera-apps \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    python3-gst-1.0 \
    build-essential \
    cmake \
    pkg-config \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# 2. Python 패키지 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 3. 소스 코드 복사
COPY . .

# HailoRT 설치의 경우, 로컬에 저장된 .whl 파일을 통해 설치해야 함.
# 예: RUN pip install hailort-4.X.X-cp310-cp310-linux_aarch64.whl

# 기본 실행 스크립트 지정 (추후 main.py 작성 시 동작)
CMD ["python", "src/main.py"]
