# Lullian external-validation environment (repository-only; never shipped).
#
# Separate Linux/CI environment for the host-level release gates. These tools are
# NOT Lullian runtime dependencies — the shipped skill package has none.
#
# Build (from F:\lullian):
#   docker build -t lullian-extval:linux -f external-validation-ci/Dockerfile external-validation-ci
#   (place skillspector-2.11.2-py3-none-any.whl in external-validation-ci/ first)
#
# Validate a shipped artifact copy:
#   docker run --rm -v <shipped-copy>:/workspace/lullian:ro lullian-extval:linux <command>

FROM python:3.13-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates git nodejs npm \
 && rm -rf /var/lib/apt/lists/*

# Static/security scanners (Tier 1 coverage)
RUN pip install --no-cache-dir semgrep bandit pip-audit
COPY skillspector-2.11.2-py3-none-any.whl /tmp/
RUN pip install --no-cache-dir /tmp/skillspector-2.11.2-py3-none-any.whl && rm /tmp/skillspector-2.11.2-py3-none-any.whl
RUN curl -sSfL https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_linux_x64.tar.gz \
      | tar -xz -C /usr/local/bin gitleaks
RUN curl -sSfL https://github.com/google/osv-scanner/releases/download/v2.6.0/osv-scanner_linux_amd64 \
      -o /usr/local/bin/osv-scanner && chmod +x /usr/local/bin/osv-scanner

# NVIDIA SkillEvaluator (security extra; tier2/tier3 extras intentionally absent
# — they require provider credentials / agent CLIs supplied at run time)
RUN pip install --no-cache-dir "skillevaluator[security] @ git+https://github.com/NVIDIA/SkillEvaluator.git@v0.4.0"

# Official Agent Skills reference CLI (skills-ref) via npm
RUN npm install -g --silent skills-ref@0.1.5

WORKDIR /workspace
CMD ["/bin/bash"]
