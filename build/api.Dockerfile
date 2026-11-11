ARG NODE_IMAGE
ARG RUST_IMAGE
FROM ${RUST_IMAGE} AS zhs-build
WORKDIR /build/zhs
COPY courseflow-zhs/ ./
RUN cargo test --locked && cargo build --release --locked

FROM ${NODE_IMAGE} AS node-deps
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends python3 make g++ && rm -rf /var/lib/apt/lists/*
COPY framework/package.json framework/package-lock.json ./
RUN npm ci
FROM node-deps AS production-deps
RUN npm prune --omit=dev

FROM ${NODE_IMAGE} AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates chromium fonts-noto-cjk python3 python3-venv tar && rm -rf /var/lib/apt/lists/*
COPY courseflow-chaoxing/requirements.txt /opt/cx-requirements.txt
RUN python3 -m venv /opt/cx-venv && /opt/cx-venv/bin/pip install --no-cache-dir -r /opt/cx-requirements.txt
WORKDIR /app
COPY --from=production-deps /app/node_modules ./node_modules
COPY framework/package.json framework/LICENSE ./
COPY framework/src ./src
COPY courseflow-zhs/courseflow.module.json courseflow-zhs/LICENSE /opt/courseflow-modules/zhs/
COPY --from=zhs-build /build/zhs/target/release/courseflow-zhs /opt/courseflow-modules/zhs/target/release/courseflow-zhs
COPY courseflow-chaoxing/courseflow.module.json courseflow-chaoxing/main.py courseflow-chaoxing/requirements.txt courseflow-chaoxing/LICENSE courseflow-chaoxing/NOTICE.md /opt/courseflow-modules/cx/
COPY courseflow-chaoxing/cx /opt/courseflow-modules/cx/cx
COPY tools/ /opt/courseflow-tools/
COPY sources.lock.json /opt/courseflow-tools/sources.lock.json
RUN chmod -R a+rX /app /opt/courseflow-modules /opt/courseflow-tools && chmod 755 /opt/courseflow-modules/cx/main.py /opt/courseflow-tools/entrypoint.sh && mkdir /data && chown node:node /data
ARG FRAMEWORK_REVISION
ARG ZHS_REVISION
ARG CX_REVISION
ARG RELEASE_VERSION
LABEL org.opencontainers.image.title="Courseflow API" \
      org.opencontainers.image.source="https://github.com/Course-Flow-Lab/courseflow-docker" \
      org.opencontainers.image.licenses="MIT AND GPL-3.0-only" \
      org.opencontainers.image.version="${RELEASE_VERSION}" \
      org.opencontainers.image.revision="${FRAMEWORK_REVISION}" \
      tech.snowlilt.courseflow.zhs-revision="${ZHS_REVISION}" \
      tech.snowlilt.courseflow.cx-revision="${CX_REVISION}"
ENV NODE_ENV=production CF_DATA_DIR=/data CF_BIND=0.0.0.0:8101 CF_CHROMIUM=/usr/bin/chromium PATH="/opt/cx-venv/bin:${PATH}"
USER node
EXPOSE 8101
ENTRYPOINT ["/opt/courseflow-tools/entrypoint.sh"]
CMD ["node", "src/main.ts", "serve"]

FROM runtime AS test
USER root
COPY framework/ /check/courseflow-framework/
COPY courseflow-zhs/ /check/courseflow-zhs/
COPY --from=zhs-build /build/zhs/target/release/courseflow-zhs /check/courseflow-zhs/target/release/courseflow-zhs
COPY courseflow-chaoxing/ /check/courseflow-chaoxing/
COPY --from=node-deps /app/node_modules /check/courseflow-framework/node_modules
COPY test-source.mjs /check/test-source.mjs
RUN chown -R node:node /check && chmod -R u+rX /check
USER node
ENV CF_CX_PYTHON=/opt/cx-venv/bin/python PYTHONDONTWRITEBYTECODE=1
WORKDIR /check/courseflow-framework
RUN npm run typecheck && node ../test-source.mjs && cd ../courseflow-chaoxing && python -m unittest discover -s tests -v
