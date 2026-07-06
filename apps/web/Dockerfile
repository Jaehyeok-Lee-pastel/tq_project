# --- build stage ---
FROM node:20-alpine AS build
WORKDIR /app
ARG VITE_API_BASE_URL
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_SUPABASE_URL=$VITE_SUPABASE_URL
ENV VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY
COPY package*.json ./
RUN npm install
COPY . .
# VITE_* vars are inlined at build time. Pass with --build-arg + ARG/ENV for a
# real deploy; defaults point at http://localhost:8000.
RUN npm run build

# --- serve stage ---
FROM nginx:alpine
ENV PORT=8080
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
