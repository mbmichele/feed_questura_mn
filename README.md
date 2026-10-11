# feed_questura_mn

## 📡 Feed pubblico

**[https://mbmichele.github.io/feed_questura_mn/feed.xml](https://mbmichele.github.io/feed_questura_mn/feed.xml)**

```
https://mbmichele.github.io/feed_questura_mn/feed.xml
```

Pagina di presentazione: [https://mbmichele.github.io/feed_questura_mn/](https://mbmichele.github.io/feed_questura_mn/)

Questo è l'URL da incollare in un lettore RSS (Feedly, NetNewsWire, Thunderbird,
ecc.). Il blocco sopra è pensato per essere copiato facilmente con un click
sull'icona di copia che GitHub mostra passandoci sopra; il link in grassetto
è invece cliccabile direttamente.

Feed RSS **non ufficiale** dei comunicati della Questura di Mantova, generato
per scraping da:

- <https://questure.poliziadistato.it/it/Mantova/archivio/view/5730dc9d1c604802219614>
- <https://questure.poliziadistato.it/it/Mantova/archivio/category/5730dc9f408ec587750440>
- <https://questure.poliziadistato.it/it/archivio/rss> (feed nazionale, filtrato sulle sole voci relative a Mantova)
- <https://feeds.feedburner.com/poliziadistato/wOCUxU193aB> (feed FeedBurner, filtrato allo stesso modo sulle sole voci relative a Mantova)
- <https://politepaul.com/fd/7jQTccRVOive.xml> (mirror RSS di terze parti della sola pagina di archivio di Mantova: nessun filtro, è già specifico per Mantova)

Il feed generato (`docs/feed.xml`) contiene titolo, data, descrizione e link
di ogni comunicato, in formato RSS 2.0.

Progetto non affiliato alla Polizia di Stato né al Ministero dell'Interno.

## Come funziona

- `scripts/generate_feed.py` scarica le due pagine di archivio e individua
  ogni comunicato nel blocco `<div class="elenco_notizie notizia">`,
  estraendone titolo e link da `h3 > a`, la data (formato `gg-mm-aaaa`) da
  `div.content > p > em` e la descrizione dal resto del testo in
  `div.content`. L'etichetta di categoria (`span.label`, es. "Iniziative",
  "I fatti del giorno") sta in un tag a parte e viene scartata
  automaticamente, a prescindere da quante e quali categorie compaiono.
- Scarica anche tre feed RSS: quello nazionale e quello FeedBurner (dai
  quali tiene solo le voci che citano "mantova" in titolo, descrizione,
  link o categoria) e il mirror PolitePaul, che converte già in RSS la
  sola pagina di archivio di Mantova — da quest'ultimo tiene tutte le voci
  senza filtrare, perché sono già specifiche di Mantova.
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
   [https://mbmichele.github.io/feed_questura_mn/](https://mbmichele.github.io/feed_questura_mn/),
   e il feed su
   [https://mbmichele.github.io/feed_questura_mn/feed.xml](https://mbmichele.github.io/feed_questura_mn/feed.xml)
   (vedi anche la sezione "📡 Feed pubblico" in cima a questo file).

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

### 5. Esecuzione manuale e debug

Il workflow può anche essere lanciato a mano da **Actions → Aggiorna feed
RSS Questura Mantova → Run workflow**.

Da lì è disponibile anche l'opzione **"Salva come artifact... debug_dump"**:
se attivata, il workflow salva l'HTML/XML grezzo scaricato da ognuna delle
quattro fonti in un artifact scaricabile ("debug-dump", conservato 7
giorni), e nei log della run compaiono anche dei conteggi diagnostici
(`[INFO]`), ad es.:

```
[INFO] https://questure.poliziadistato.it/...: HTTP 200, 48213 byte
[INFO] https://questure.poliziadistato.it/...: 0 comunicati estratti
[INFO]   occorrenze di 'elenco_notizie' trovate nell'HTML: 0
[INFO] https://questure.poliziadistato.it/it/archivio/rss: 40 item totali nel feed
[INFO] https://questure.poliziadistato.it/it/archivio/rss: 3 item su Mantova dopo il filtro
```

Questo permette di distinguere subito due casi molto diversi:

- **il download fallisce** (righe `[WARN] impossibile scaricare...`, HTTP
  403 o simili) → è un problema di anti-bot/rete;
- **il download riesce ma non si trova nulla** (HTTP 200 ma 0 comunicati/0
  link con il pattern atteso) → la struttura HTML del sito o del feed è
  cambiata rispetto a quella prevista dal parser, e vanno aggiornati i
  selettori in `scripts/generate_feed.py`.

In quest'ultimo caso, l'artifact `debug-dump` contiene l'HTML/XML reale
scaricato dal runner: è il modo più rapido per capire cosa aggiustare nel
parser.

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

## Richieste successive al prompt originale

Il pacchetto è stato aggiornato rispetto al prompt originale con queste
richieste successive, riportate qui per completezza (in ordine cronologico):

1. Inserito anche uno **schedule interno** di GitHub Actions (`cron: "0 * * * *"`),
   in aggiunta al cronjob esterno, così il workflow gira ogni ora anche
   senza dipendere da un servizio esterno.
2. Aggiunto un **sistema anti-bot** che simula un accesso da browser reale:
   header completi di Chrome su Windows, sessione persistente con cookie,
   ritardo casuale fra le richieste.
3. Aggiunta come ulteriore fonte il feed
   `https://feeds.feedburner.com/poliziadistato/wOCUxU193aB`, filtrato
   anch'esso sulle sole voci relative a Mantova.
4. Reso il commit/push resiliente a run concorrenti (rebase + retry invece
   di fallire su "fetch first" quando cron interno ed esterno scattano
   quasi insieme), e aggiunta diagnostica/debug dump (log `[INFO]` con
   conteggi e artifact opzionale con l'HTML/XML grezzo scaricato) per
   individuare perché il parser non trova comunicati anche quando il
   download riesce.
5. Aggiunta in cima al README una sezione "📡 Feed pubblico" con l'URL del
   feed sia come link cliccabile sia in un blocco di codice copiabile, e
   resi cliccabili anche gli altri link (fonti, GitHub Pages) nel resto del
   file.
6. Corretto il parser delle pagine di archivio sulla base dell'HTML reale
   (fornito dall'utente): il pattern `cs_context.jsp?...id_context=...`
   ipotizzato inizialmente non esiste sul sito. I comunicati si trovano
   invece in blocchi `<div class="elenco_notizie notizia">`, con titolo e
   link in `h3 > a`, data in formato gg-mm-aaaa dentro `div.content > p >
   em`, e l'etichetta di categoria in uno `<span class="label">` separato
   (non termina con una virgola, come invece ipotizzato in origine).
7. Aggiunta come fonte ulteriore il mirror RSS di terze parti
   `https://politepaul.com/fd/7jQTccRVOive.xml`, che converte già in RSS
   la pagina di archivio di Mantova: a differenza delle altre fonti RSS,
   qui non si applica il filtro testuale "mantova" perché ogni voce è già
   specifica di Mantova per definizione.
8. Corretta la strategia di push concorrente: il rebase introdotto al
   punto 4 può andare in conflitto su `docs/feed.xml`, perché quel file è
   rigenerato per intero a ogni run (contiene sempre un `lastBuildDate`
   diverso) e un merge testuale riga per riga fallisce quasi sempre. La
   nuova strategia non unisce mai i contenuti: a ogni tentativo fallito
   riappoggia lo stesso commit (con il feed di questa run) sull'ultimo
   stato remoto con `git reset --soft` + ricommit, invece di fare
   `git rebase`. Se nel frattempo un'altra run ha già pubblicato un feed
   identico, il passo si conclude senza errori invece di tentare un
   commit vuoto.

## Prompt aggiornato (consolidato)

Il prompt originale più tutte le richieste successive elencate sopra,
riscritti come un unico prompt coerente: è la versione da riusare per
rigenerare il pacchetto da zero, allo stato attuale del progetto.

> Voglio un repository GitHub che generi un feed RSS pubblico non ufficiale
> a partire dagli elementi pubblicati alle pagine:
> https://questure.poliziadistato.it/it/Mantova/archivio/view/5730dc9d1c604802219614
> https://questure.poliziadistato.it/it/Mantova/archivio/category/5730dc9f408ec587750440
>
> e dai feed:
> - https://questure.poliziadistato.it/it/archivio/rss (filtrando solo le voci che riguardano Mantova)
> - https://feeds.feedburner.com/poliziadistato/wOCUxU193aB (filtrando solo le voci che riguardano Mantova)
> - https://politepaul.com/fd/7jQTccRVOive.xml (mirror RSS di terze parti già specifico per Mantova: nessun filtro)
>
> Il flusso RSS deve contenere titolo, data, descrizione e link di ogni
> comunicato.
>
> Requisiti:
> - Script Python (requests + BeautifulSoup) che fa scraping delle pagine,
>   individua ogni comunicato nel blocco `<div class="elenco_notizie
>   notizia">`, estraendo titolo e link da `h3 > a`, la data (formato
>   gg-mm-aaaa) da `div.content > p > em` e la descrizione dal resto del
>   testo in `div.content`. L'etichetta di categoria (`span.label`, es.
>   "Iniziative", "I fatti del giorno") sta in un tag a parte e va scartata
>   automaticamente, indipendentemente da quante e quali categorie
>   compaiono.
> - Le richieste HTTP devono simulare un accesso da browser reale (non la
>   libreria HTTP "nuda"): header completi tipo Chrome su Windows
>   (User-Agent, Accept, Accept-Language, Sec-Fetch-*, Sec-Ch-Ua, Referer),
>   sessione persistente con cookie condivisi fra le richieste, e un
>   piccolo ritardo casuale fra una richiesta e l'altra, per ridurre i falsi
>   positivi delle protezioni anti-bot del sito.
> - Genera un file docs/feed.xml (RSS 2.0 valido, con guid, pubDate in
>   formato RFC 822, fuso orario Europe/Rome).
> - GitHub Action con doppio trigger orario: uno schedule interno di GitHub
>   Actions (ogni ora) come backup automatico, più workflow_dispatch,
>   innescabile anche da un cronjob esterno (es. cron-job.org) che chiama
>   l'API di GitHub per lanciare il workflow ogni ora. In entrambi i casi il
>   workflow rigenera il feed e fa commit/push solo se il contenuto cambia;
>   il push deve essere resiliente a run concorrenti, senza fallire su
>   "fetch first" quando i due trigger scattano quasi insieme. Dato che il
>   feed è rigenerato per intero a ogni run (contiene sempre un
>   lastBuildDate diverso), la strategia di retry non deve provare a
>   unire i contenuti con un rebase/merge testuale (va quasi sempre in
>   conflitto): a ogni tentativo fallito deve riappoggiare lo stesso
>   commit sull'ultimo stato remoto (fetch + reset soft + ricommit) e
>   riprovare il push, concludendosi senza errori se nel frattempo il
>   remoto ha già un contenuto identico.
> - Diagnostica integrata nello script (log con conteggi di byte scaricati,
>   comunicati estratti per fonte, item totali/filtrati per i feed RSS) e
>   un'opzione di debug (parametro del workflow_dispatch) che salva come
>   artifact scaricabile l'HTML/XML grezzo scaricato da ogni fonte, per
>   poter diagnosticare eventuali cambi di struttura del sito.
> - docs/index.html minimale con link al feed, per la pubblicazione tramite
>   GitHub Pages (branch main, cartella /docs).
> - README con: istruzioni di setup (creazione repo, GitHub Pages, PAT e
>   configurazione del cronjob esterno); una sezione in cima con l'URL
>   pubblico del feed generato sia come link cliccabile sia in un blocco di
>   codice facilmente copiabile; questo stesso prompt aggiornato incluso,
>   per poter rigenerare il pacchetto in futuro.
> - Consegna il tutto come pacchetto .zip scaricabile, con un numero di
>   versione nel nome del file.

## Licenza

Contenuto tecnico (script, workflow) rilasciato senza garanzie, per uso
personale/civico. I contenuti dei comunicati restano di proprietà della
Polizia di Stato.
