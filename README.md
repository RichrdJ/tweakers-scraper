<div align="center">
  <img src="https://raw.githubusercontent.com/RichrdJ/tweakers-scraper/main/docs/banner.svg" alt="Tweakers Monitor" width="100%"/>
</div>

<br>

<div align="center">
  <a href="https://github.com/RichrdJ/tweakers-scraper/releases"><img src="https://img.shields.io/github/v/release/RichrdJ/tweakers-scraper?color=e8770e&label=release&style=flat-square" alt="Release"/></a>
  <a href="https://github.com/RichrdJ/tweakers-scraper/pkgs/container/tweakers-scraper"><img src="https://img.shields.io/badge/ghcr.io-tweakers--scraper-e8770e?style=flat-square&logo=docker&logoColor=white" alt="Docker"/></a>
  <a href="https://github.com/RichrdJ/tweakers-scraper/actions"><img src="https://img.shields.io/github/actions/workflow/status/RichrdJ/tweakers-scraper/docker.yml?style=flat-square&label=build&color=e8770e" alt="Build"/></a>
</div>

<br>

Nooit meer een deal missen op Tweakers Vraag & Aanbod. Stel zoekopdrachten in en ontvang direct een melding zodra er een nieuwe advertentie verschijnt — via Discord, Telegram of gewoon in de webinterface.

---

## ✨ Functies

- **Realtime monitoring** — checkt je zoekopdrachten op instelbaar interval (standaard 5 min)
- **Alleen nieuwe advertenties** — de eerste run zaait bestaande items in zonder meldingen, daarna krijg je enkel wat er nieuw bijkomt
- **Discord & Telegram** — rijke meldingen met foto, prijs, locatie en verkoper
- **Gereserveerd-status** — ziet wanneer een advertentie als gereserveerd is gemarkeerd
- **Webinterface met dark mode** — overzichtelijk dashboard, zoekopdrachten beheren en instellingen
- **Docker-ready** — één `docker-compose.yml` en je bent live
- **Persistente opslag** — SQLite met WAL-mode, data overleeft container-restarts
- **NL / EN** — interface volledig tweetalig

---

## 🚀 Snel starten

### Vereisten
- Docker + Docker Compose

### 1. Maak een `docker-compose.yml`

```yaml
services:
  tweakers-monitor:
    image: ghcr.io/richrdj/tweakers-scraper:latest
    pull_policy: always
    container_name: tweakers-monitor
    ports:
      - "8001:8000"
    volumes:
      - tw_data:/data
    restart: unless-stopped

volumes:
  tw_data:
```

### 2. Start de container

```bash
docker compose up -d
```

### 3. Open de webinterface

Ga naar `http://localhost:8001` (of het IP van je server).

---

## ⚙️ Configuratie

Alle instellingen zijn te beheren via de webinterface onder **Instellingen**:

| Instelling | Beschrijving |
|---|---|
| Discord Webhook URL | Maak aan via Kanaalinstellingen → Integraties → Webhooks |
| Telegram Bot Token | Aanmaken via [@BotFather](https://t.me/BotFather) |
| Telegram Chat ID | Opvragen via [@userinfobot](https://t.me/userinfobot) |

---

## 🔍 Zoekopdrachten toevoegen

1. Ga naar [tweakers.net/aanbod/zoeken](https://tweakers.net/aanbod/zoeken/) en stel je filters in
2. Kopieer de volledige URL uit de adresbalk
3. Plak de URL in de webinterface onder **Zoekopdrachten → Nieuwe zoekopdracht**

**Ondersteunde URL-formaten:**
```
https://tweakers.net/aanbod/zoeken/?keyword=rtx+4080
https://tweakers.net/aanbod/zoeken/?keyword=iphone&priceFrom=100&priceTo=400
https://tweakers.net/serie/1098/iphone/aanbod/
https://tweakers.net/smartphones/apple/iphone-16_p1657500/aanbod/
```

---

## 📬 Meldingen

### Discord
Meldingen verschijnen als embed met foto, prijs, locatie, verkoper en een directe link naar de advertentie. Gereserveerde items krijgen een ⚠️ markering.

### Telegram
Stuurt een foto-bericht (als beschikbaar) met prijs, locatie, verkoper en een klikbare link.

> **Tip:** Gebruik de **Test**-knop in de instellingen om te controleren of meldingen correct binnenkomen.

---

## 🛠️ Zelf bouwen

```bash
git clone https://github.com/RichrdJ/tweakers-scraper.git
cd tweakers-scraper
docker compose up -d --build
```

---

## 📦 Stack

| Onderdeel | Technologie |
|---|---|
| Backend | Python 3.12 + Flask |
| Scraper | BeautifulSoup4 + lxml |
| Database | SQLite (WAL-mode) |
| Meldingen | Discord Webhooks · Telegram Bot API |
| Frontend | Bootstrap 5.3 + Bootstrap Icons |
| Container | Docker / Docker Compose |
| CI/CD | GitHub Actions → GHCR |

---

## 📄 Licentie

MIT — doe er mee wat je wilt.
