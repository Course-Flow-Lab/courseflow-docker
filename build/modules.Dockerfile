ARG RUST_IMAGE
ARG NODE_IMAGE
FROM ${RUST_IMAGE} AS zhs
WORKDIR /build/zhs
COPY zhs/ ./
RUN cargo test --locked && cargo build --release --locked

FROM ${NODE_IMAGE} AS unipus
WORKDIR /build/unipus
COPY unipus/package.json unipus/package-lock.json ./
RUN npm ci
COPY unipus/ ./
RUN npm run build && node --check index.mjs

FROM scratch AS artifacts
COPY --from=zhs /build/zhs/target/release/courseflow-zhs /zhs/target/release/courseflow-zhs
COPY --from=unipus /build/unipus/index.mjs* /unipus/
