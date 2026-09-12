# feed_questura_mn

Feed RSS **non ufficiale** dei comunicati della Questura di Mantova, generato
per scraping da:

- `https://questure.poliziadistato.it/it/Mantova/archivio/view/5730dc9d1c604802219614`
- `https://questure.poliziadistato.it/it/Mantova/archivio/category/5730dc9f408ec587750440`
- `https://questure.poliziadistato.it/it/archivio/rss` (feed nazionale, filtrato sulle sole voci relative a Mantova)

Il feed generato (`docs/feed.xml`) contiene titolo, data, descrizione e link
di ogni comunicato, in formato RSS 2.0.

Progetto non affiliato alla Polizia di Stato né al Ministero dell'Interno.

## Come funziona

- `scripts/generate_feed.py` scarica le pagine sopra indicate, individua ogni
  comunicato tramite i link di dettaglio (pattern `cs_context.jsp?...id_context=...`),
  risale al blocco di testo che lo contiene ed estrae titolo, data, link e
  descrizione. Le etichette di categoria (che terminano sempre con una
  virgola, es. "Per il cittadino,") vengono scartate automaticamente.
- Il risultato viene scritto in `docs/feed.xml`.
- `docs/index.html` è una pagina minimale che linka il feed, pubblicata
  tramite GitHub Pages.
- Il workflow GitHub Actions (`.github/workflows/update-feed.yml`) ha
  **due** trigger, entrambi orari:
  - uno **schedule interno** di GitHub Actions (`cron: "0 * * * *"`, in
    UTC), come backup automatico;
  - il trigger `workflow_dispatch`, innescabile ogni ora anche da un
    cronjob esterno tramite l'API di GitHub, per un orario più puntuale
    (lo schedule di Actions è "best effort" e può slittare di qualche
    minuto sui runner condivisi).

  In ogni caso, il workflow rigenera il feed e fa commit/push solo se il
  contenuto è cambiato.

## Setup

### 1. Crea il repository

1. Crea un nuovo repository su GitHub (es. `feed_questura_mn`), pubblico.
2. Carica il contenuto di questo pacchetto nel branch `main`.

### 2. Attiva GitHub Pages

1. Vai su **Settings → Pages**.
2. In **Source**, seleziona **Deploy from a branch**.
3. Branch: **main**, cartella: **/docs**.
4. Salva. Dopo qualche minuto il sito sarà raggiungibile su
   `https://mbmichele.github.io/feed_questura_mn/`, e il feed su
   `https://mbmichele.github.io/feed_questura_mn/feed.xml`.

### 3. Crea un Personal Access Token (PAT)

Il workflow usa il `GITHUB_TOKEN` automatico di Actions per fare commit e
push (permessi `contents: write` già configurati), **quindi non è
necessario creare un PAT per il funzionamento del workflow stesso**.

Un PAT serve invece al cronjob esterno per **innescare** il workflow via
API (l'endpoint `workflow_dispatch` richiede autenticazione):

1. Vai su **Settings personali di GitHub → Developer settings → Personal
   access tokens → Fine-grained tokens** (o *Tokens (classic)*).
2. Crea un token con permesso **Actions: Read and write** limitato al
   repository `feed_questura_mn` (fine-grained) oppure scope `repo` /
   `workflow` (classic).
3. Copia il token: servirà al passo successivo. Conservalo con cura, non va
   mai committato nel repository.

### 4. Configura il cronjob esterno (es. cron-job.org)

Il repository ha già uno schedule interno orario su GitHub Actions
(`cron: "0 * * * *"`, in UTC): di per sé farebbe già girare il workflow
ogni ora. Il cronjob esterno è complementare (non alternativo), pensato per
avere un secondo innesco puntuale via API, indipendente dai tempi "best
effort" dello scheduler di GitHub Actions.

1. Crea un account su [cron-job.org](https://cron-job.org) (o servizio
   equivalente).
2. Crea un nuovo cronjob con:
   - **URL**:
     `https://api.github.com/repos/mbmichele/feed_questura_mn/actions/workflows/update-feed.yml/dispatches`
   - **Metodo**: `POST`
   - **Intervallo**: ogni ora (es. `0 * * * *`)
   - **Header**:
     - `Authorization: Bearer <IL_TUO_PAT>`
     - `Accept: application/vnd.github+json`
     - `Content-Type: application/json`
   - **Body** (JSON):
     ```json
     {"ref": "main"}
     ```
3. Salva e attiva il cronjob. Ogni ora invierà una richiesta che avvia il
   workflow su GitHub; il feed viene rigenerato e, se cambiato, committato
   automaticamente.

### 5. Esecuzione manuale

Il workflow può anche essere lanciato a mano da **Actions → Aggiorna feed
RSS Questura Mantova → Run workflow**.

## Sviluppo locale

```bash
pip install -r requirements.txt
python scripts/generate_feed.py
```

Il file generato si trova in `docs/feed.xml`.

## Note

- Il sito `questure.poliziadistato.it` applica protezioni anti-bot. Per
  ridurne i falsi positivi, lo script:
  - usa un set di header realistico da browser desktop (Chrome su Windows:
    `User-Agent`, `Accept`, `Accept-Language`, `Sec-Fetch-*`, `Sec-Ch-Ua`,
    `Referer`, ecc.), invece dello User-Agent generico delle librerie HTTP;
  - mantiene una sessione HTTP persistente (`requests.Session`), con i
    cookie condivisi fra una richiesta e l'altra come farebbe un browser;
  - attende un intervallo casuale (1.5–3.5 secondi) fra una richiesta e
    l'altra, per non generare un pattern di traffico "a raffica".

  Nonostante questo, alcune protezioni anti-bot bloccano comunque le
  richieste in base all'indirizzo IP di provenienza (non solo agli header):
  se lo scraping continua a fallire con errore 403 anche con questi
  accorgimenti, il problema è probabilmente a livello di IP/rete più che di
  header, e va verificato eseguendo il workflow direttamente sui runner di
  GitHub Actions.
- Trattandosi di scraping non ufficiale, la struttura HTML delle pagine può
  cambiare nel tempo: in tal caso occorre aggiornare i selettori in
  `scripts/generate_feed.py`.

## Prompt originale (per rigenerare il pacchetto in futuro)

Il pacchetto è stato generato a partire dal seguente prompt, conservato qui
per poterlo riutilizzare o adattare in futuro:

> Voglio un repository GitHub che generi un feed RSS pubblico non ufficiale
> a partire dagli elementi pubblicati alle pagine:
> https://questure.poliziadistato.it/it/Mantova/archivio/view/5730dc9d1c604802219614
> https://questure.poliziadistato.it/it/Mantova/archivio/category/5730dc9f408ec587750440
>
> e dal feed https://questure.poliziadistato.it/it/archivio/rss solo quelle che riguardano Mantova
>
> Il flusso RSS deve contenere titolo, data, descrizione e link di ogni
> comunicato.
>
> Requisiti:
> - Script Python (requests + BeautifulSoup) che fa scraping della pagina,
>   individua ogni comunicato tramite i link che puntano al dettaglio
>   (pattern "cs_context.jsp?...id_context=..."), risale al blocco di testo
>   che lo contiene ed estrae titolo, data, link e descrizione. Le etichette
>   di categoria (che terminano sempre con una virgola, es. "per il
>   cittadino,") vanno scartate automaticamente, indipendentemente da quante
>   e quali sono.
> - Genera un file docs/feed.xml (RSS 2.0 valido, con guid, pubDate in
>   formato RFC 822, fuso orario Europe/Rome).
> - GitHub Action con solo "workflow_dispatch" (nessuno schedule interno):
>   deve essere innescabile da un cronjob esterno (es. cron-job.org) che
>   chiama l'API di GitHub per lanciare il workflow ogni ora; il workflow
>   rigenera il feed e fa commit/push solo se il contenuto cambia.
> - docs/index.html minimale con link al feed, per la pubblicazione tramite
>   GitHub Pages (branch main, cartella /docs).
> - README con istruzioni di setup (creazione repo, GitHub Pages, PAT e
>   configurazione del cronjob esterno) e con questo stesso prompt incluso,
>   per poter rigenerare il pacchetto in futuro.
> - Consegna il tutto come pacchetto .zip scaricabile, con un numero di
>   versione nel nome del file.

## Licenza

Contenuto tecnico (script, workflow) rilasciato senza garanzie, per uso
personale/civico. I contenuti dei comunicati restano di proprietà della
Polizia di Stato.
