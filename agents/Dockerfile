FROM python:3.12-slim
WORKDIR /app
COPY agents /app/agents
# The default image is offline and installs no cloud SDK.
USER 65534:65534
ENTRYPOINT ["python", "-m", "agents.rag"]
CMD ["DBH 誤差怎麼計算？"]
