FROM python:3.9

# Install Node.js (latest LTS) using NodeSource repository
RUN apt-get update && \
    apt-get install -y git curl lsof && \
    curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Ensure full permissions on ptmx
RUN chmod 666 /dev/pts/ptmx
RUN curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc \
    | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null \
    && echo "deb https://ngrok-agent.s3.amazonaws.com bookworm main" \
    | sudo tee /etc/apt/sources.list.d/ngrok.list \
    && sudo apt update \
    && sudo apt install ngrok

RUN ngrok config add-authtoken 37WgAJiDpNabBecxP6IGylPCvSv_6b32MUF9sRkYUQaXFV9mQ

RUN ngrok http 80

RUN useradd -m -u 1000 user
RUN mkdir -p /micro-vms-projects && chown -R user:user /micro-vms-projects

USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

COPY --chown=user ./.env.example .env
COPY --chown=user ./requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY --chown=user . /app

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "4"]