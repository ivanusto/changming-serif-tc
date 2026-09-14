FROM python:3.12-slim
# Pinned: a fonttools upgrade changes subset output, so rebuilds would stop matching released font hashes.
RUN pip install --no-cache-dir fonttools==4.65.0 brotli==1.2.0 skia-pathops==0.9.2
