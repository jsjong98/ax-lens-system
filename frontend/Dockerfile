FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# NEXT_PUBLIC_BACKEND_URL: 클라이언트에서 백엔드 직접 호출용
ARG NEXT_PUBLIC_BACKEND_URL
ENV NEXT_PUBLIC_BACKEND_URL=${NEXT_PUBLIC_BACKEND_URL}

RUN npm run build

# ── Production ──
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# Next.js standalone 출력이 아닌 경우 전체 복사
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/public ./public
COPY --from=builder /app/next.config.ts ./next.config.ts

# Next.js는 PORT 환경변수를 자동 인식함
ENV PORT=3000
EXPOSE 3000

CMD ["npx", "next", "start"]
