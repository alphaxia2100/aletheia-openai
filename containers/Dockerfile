# Reference execution image for Aletheia's portable runtime utilities.
# Pin PYTHON_IMAGE to an immutable digest in a release pipeline; the version tag is kept here so
# a user can build on either Apple Silicon or x86-64 without changing source files.
ARG PYTHON_IMAGE=python:3.11.14-slim-bookworm
FROM ${PYTHON_IMAGE}

LABEL org.opencontainers.image.title="Aletheia portable runtime" \
      org.opencontainers.image.description="Non-root reference container for Aletheia utility execution"

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin aletheia \
    && mkdir -p /opt/aletheia/skills /opt/aletheia/tools /work \
    && chown -R aletheia:aletheia /opt/aletheia /work

# Copy only the runtime closure of the public flagship. Never copy a user .env, runs/, browser
# profile, Docker socket, or retired/experimental sibling skills into this image.
COPY --chown=aletheia:aletheia .cursor/skills/aletheia-research /opt/aletheia/skills/aletheia-research
COPY --chown=aletheia:aletheia .cursor/skills/channel-retrieval /opt/aletheia/skills/channel-retrieval
COPY --chown=aletheia:aletheia .cursor/skills/provenance-audit /opt/aletheia/skills/provenance-audit
COPY --chown=aletheia:aletheia VERSION .env.example requirements-optional.txt /opt/aletheia/
COPY --chown=aletheia:aletheia scripts/preflight.py /opt/aletheia/tools/preflight.py

# The launcher supplies the writable /work mount and a tmpfs.  Record the image closure before
# adding its local install marker; this detects accidental runtime drift without claiming release
# authenticity (that still comes from the pinned Git ref/release process).
RUN python3 /opt/aletheia/tools/preflight.py --runtime /opt/aletheia --write-manifest \
    && printf '{"schema_version":1,"managed_by":"aletheia","mode":"container-runtime"}\n' \
       > /opt/aletheia/.aletheia-install.json \
    && chmod -R a-w /opt/aletheia

USER aletheia
WORKDIR /work
ENV HOME=/home/aletheia \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONNOUSERSITE=1

CMD ["python3", "/opt/aletheia/tools/preflight.py", "--runtime", "/opt/aletheia"]
