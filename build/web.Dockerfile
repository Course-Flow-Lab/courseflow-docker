ARG NODE_IMAGE
ARG NGINX_IMAGE
FROM ${NODE_IMAGE} AS build
WORKDIR /build
COPY courseflow-webui/package.json courseflow-webui/package-lock.json ./
RUN npm ci
COPY courseflow-webui/ ./
RUN npm run check && node --test test/*.test.mjs && npm run build
FROM ${NGINX_IMAGE}
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=build /build/dist /usr/share/nginx/html
ARG WEBUI_REVISION
ARG RELEASE_VERSION
LABEL org.opencontainers.image.title="Courseflow WebUI" \
      org.opencontainers.image.source="https://github.com/Course-Flow-Lab/courseflow-docker" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="${RELEASE_VERSION}" \
      org.opencontainers.image.revision="${WEBUI_REVISION}"
USER nginx
EXPOSE 8080
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
