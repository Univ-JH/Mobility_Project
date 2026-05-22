# 1단계: Build 단계
FROM node:20-alpine AS builder

WORKDIR /app

# 패키지 정보 복사 및 의존성 설치
COPY package*.json ./
RUN npm ci

# 소스 코드 복사 및 빌드
COPY . .
# 프로덕션 빌드 실행 (Vite)
RUN npm run build

# 2단계: Production 서빙 단계 (Nginx)
FROM nginx:alpine

# Nginx 기본 설정 제거 후 커스텀 설정 복사
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 빌드된 정적 파일들을 Nginx 서빙 폴더로 복사
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
