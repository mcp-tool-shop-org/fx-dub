<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.md">English</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="docs/assets/logo.png" alt="fx-dub" width="400">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/fx-dub/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/fx-dub/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/fx-dub/"><img src="https://img.shields.io/pypi/v/fx-dub.svg" alt="PyPI"></a>
  <a href="https://pypi.org/project/fx-dub/"><img src="https://img.shields.io/pypi/pyversions/fx-dub.svg" alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT"></a>
  <a href="https://mcp-tool-shop-org.github.io/fx-dub/"><img src="https://img.shields.io/badge/landing-page-blue.svg" alt="Landing page"></a>
</p>

**Verifica un doppiaggio generato prima che qualcuno lo ascolti.**

Il tuo modello di sintesi vocale ha restituito audio stereo a 48 kHz con la durata esatta e un livello LUFS di -18, come da manuale. Ha anche pronunciato una frase che non hai mai scritto, con una voce diversa da quella del personaggio, lasciando uno spazio di due secondi nel mezzo.

Nessuno di questi elementi è visibile nei parametri di frequenza di campionamento e durata. fx-dub ti fornisce due rapporti: uno per il file audio e uno per **ciò che è stato effettivamente detto**, e termina con un codice di errore diverso da zero se una qualsiasi delle verifiche fallisce.

```bash
pip install fx-dub
```

```console
$ fxdub-dialogue docs/scenes/night-street.json words.json --only-speaker VOICE
9/10 checks pass
| PASS | line_present:0:VOICE    | Hey, how's it going?
| FAIL | no_invented_speech      | 4 unscripted word(s): not bad can't complain
| PASS | no_overlap              | clean
| PASS | no_internal_straggle    | clean
| PASS | one_voice_per_character | clean
```

Questo errore è reale. Un modello in modalità `audio reference` ha riprodotto la *dialogo* del clip di riferimento, non solo il suo timbro; quindi, una traccia destinata a contenere le battute di un personaggio ha ripetuto silenziosamente le battute dell'altro. Mixato con la registrazione originale, sembrava che due persone stessero parlando contemporaneamente. Frequenza di campionamento: perfetta. Durata: perfetta.

## I due rapporti

| | Verifiche | Rilevamenti |
|---|---|---|
| **`fxdub-receipt`** | set di file da consegnare, master a 48 kHz, livello di loudness EBU R128, profondità di attenuazione del dialogo rispetto alla traccia di sottofondo, MP4 rimuxato che contiene **entrambe** le tracce, fotogrammi intatti | doppiaggio silenzioso, doppiaggio troncato, dialogo sommerso nella traccia di sottofondo, mix che non raggiunge l'obiettivo desiderato |
| **`fxdub-dialogue`** | tutte le battute del copione presenti e nell'ordine corretto, nessuna frase inventata, nessuna sovrapposizione tra i personaggi, nessuna interruzione a metà frase, una voce per personaggio, si adatta al clip | un modello che inventa frasi, un personaggio con una voce diversa rispetto alle registrazioni precedenti, una pausa che interrompe la battuta successiva, due personaggi fusi in un'unica voce |

**Una verifica fallita è un risultato, non un bug nello strumento.** Segnalalo; non modificare mai la soglia per farlo risultare positivo. Ogni verifica cita lo standard o il difetto misurato a cui fa riferimento, in modo che tu possa discuterne sulla base delle prove.

## Il copione della scena è il contratto

La regia si trova nel copione, non nella mente del regista:

```json
{
  "clip_duration_s": 10.062,
  "lines": [
    { "speaker": "VOICE", "text": "Hey, how's it going?" },
    { "speaker": "MAC",   "text": "Not bad. Can't complain.",
      "max_gap_s": 0.15,
      "direction": "There's no pause in between. A gap here runs into VOICE's next cue." },
    { "speaker": "VOICE", "text": "Good to hear, good to hear." }
  ]
}
```

`max_gap_s` su quella riga spiega perché il verificatore rifiuta una registrazione che una soglia globale lascerebbe passare. La nota accanto indica perché il valore è 0,15 e non un altro.

`--only-speaker MAC` restringe il contratto a un singolo personaggio, ed è così che si verifica una **traccia per personaggio**: dovrebbe contenere le battute di quel personaggio e *silenzio* quando parlano gli altri. Verificare una traccia rispetto all'intera scena nasconde esattamente il bug descritto sopra.

## Ottenere una trascrizione

`fxdub-dialogue` legge una trascrizione a livello di parola con l'indicazione del parlante — `{text, start, end, speaker_id}` per word. Any diarizing ASR will do. `fxdub.vo_graphs.transcribe()` e crea il grafico ComfyUI per:

```python
from fxdub import vo_graphs

graph = vo_graphs.transcribe("<storage-key>.flac", "run/words")
# -> API-format dict, ready for your own submit path. Nothing is sent from here.
```

## Generatori di grafici

`fxdub.vo_graphs` crea anche i grafici della fase VO: progettazione vocale, riferimento audio con lo stesso motore, clonazione e sintesi vocale, unione, inserimento nella timeline, mixaggio. Esistono perché l'alternativa — digitare manualmente il JSON dell'API in una finestra di chat — produce grafici che scompaiono alla fine della sessione e reintroducono silenziosamente difetti per i quali si è già pagato.

Ogni generatore viene controllato dai rilevatori di errori del repository, quindi le configurazioni che causano veri e propri fallimenti non possono essere create accidentalmente. Due esempi di ciò che questo codifica:

- L'input "auto-grow" del nodo clone di ElevenLabs è indirizzato come `files.audio0` in fase di esecuzione — **non** il `files.item_1` che il suo schema pubblicizza — e un test preliminare accetta il nome errato senza segnalarlo.
- Il parametro `pitch_rate` di ByteDance è globale per il nodo, quindi un singolo nodo non può dare voce a due personaggi con altezze diverse. I suoi timestamp fanno riferimento a una timeline di output assoluta, quindi la soluzione consiste in un passaggio per personaggio, sovrapposto.

Creare un grafico è una funzione pura che prende gli argomenti e restituisce un `dict`. **Niente in questo pacchetto invia, carica o spende.**

## Modello di minaccia

fx-dub viene eseguito localmente e non effettua chiamate di rete di alcun tipo.

- **Dati elaborati:** solo i file che si specificano nella riga di comando: master FLAC/MP4, manifesti LUFS, testo delle didascalie, JSON della trascrizione. Scrive un rapporto nel percorso `--json` che si sceglie.
- **Dati NON elaborati:** nessuna credenziale, nessuna chiave API, nessun segreto ambientale, nessun file al di fuori dei percorsi specificati.
- **Autorizzazioni richieste:** lettura del filesystem sui file di input; scrittura del filesystem solo se si specifica `--json`.
- **Traffico di rete: nessuno.** Non c'è un client HTTP qui e l'elenco delle dipendenze in fase di esecuzione è vuoto per scelta: il CI fa fallire la build se ciò dovesse mai cambiare.
- **Telemetria: nessuna.** Nulla viene raccolto, conteggiato o trasmesso.

L'analisi dei media si basa esclusivamente sulle librerie standard: i file FLAC `STREAMINFO` e gli atomi MP4 vengono decodificati direttamente anziché essere passati a un programma esterno `ffprobe`. Un input non valido produce una verifica fallita, non un crash. Politica completa in [SECURITY.md](SECURITY.md).

## Codici di uscita

| Codice | Significato |
|---|---|
| `0` | tutte le verifiche sono state superate |
| `1` | l'audio non ha rispettato il contratto: leggi il rapporto |
| `2` | lo strumento non è riuscito a essere eseguito: percorso errato, JSON non valido, parlante sconosciuto |

`1` and `2` stay distinct on purpose: in CI the first wants its receipt read, the
second means the invocation is wrong. Errors print `{code, message, hint}` on
stderr; `--debug` re-raises instead.

## La pipeline che questi rapporti verificano

fx-dub è iniziato come una pipeline di doppiaggio nativa di ComfyUI e lo è ancora. Viene eseguito su [Comfy Cloud](https://cloud.comfy.org):

```
video ─► describe (Florence-2, pinned, single mid-clip frame)
              │ caption.txt
              ▼
        audio prompt (positive claims only — negation collapses in audio-text models)
              ├──────────► ambience bed (ElevenLabs eleven_sfx_v2, 48 kHz, exact duration)
              │                    │ stem_bed.flac
   your script ──────────► dialogue (per-character passes, layered on an absolute timeline)
                                   │ stem_vo.flac
                                   ▼
                    mix bus (48 kHz · dialogue-anchored · −18 LUFS)
                                   │ mix.flac + LUFS manifests
                                   ▼
                        re-mux ─► dubbed.mp4
```

> **"Re-mux"** = re-multiplex: la traccia audio finale viene riscritta nel contenitore video, senza alterare i pixel. Non è un errore di battitura per "remix": il mixaggio avviene in una fase precedente; questa è la fase che ti fornisce un `dubbed.mp4` riproducibile.

**Regola il livello del segnale audio in base al misuratore, non in base a valori memorizzati.** I motori differiscono di 8 dB sulla stessa riga: sostituire un motore TTS con un altro ha spostato una traccia vocale da -18,34 a -25,03 LUFS. Riutilizzare il guadagno fisso della ricetta precedente avrebbe abbassato il volume del dialogo di 7 dB, mentre tutte le altre verifiche sarebbero rimaste positive.

## Cosa c'è di onesto in questo progetto

- **Le didascalie trasmettono significato, non tempistiche.** Una pipeline basata sulle didascalie è adatta per ambienti e dialoghi; non sincronizzerà mai il suono di una porta che sbatte solo con la prosa. Per ottenere un impatto maggiore, sono necessarie delle tempistiche precise, ovvero una sequenza temporale degli eventi: la [Knowledge Base](docs/knowledge-base.md#stage-2b--direct-videoaudio-the-sync-first-alternative) mappa i modelli diretti video→audio che lo fanno in modo nativo e le relative licenze.
- **Una descrizione di una scena non è una sceneggiatura.** Scrivi le parole che i tuoi personaggi pronunciano; la pipeline fa sì che suonino correttamente.
- **L'identità vocale non è gratuita.** Le voci create tramite prompt non sono deterministiche, *indipendentemente dal seed* — una voce che approvi non può essere richiamata eseguendo nuovamente lo stesso prompt. Definisci le voci una sola volta, conserva l'audio approvato e poi utilizzalo o modificalo in seguito. La clonazione tra diversi motori non preserva nemmeno l'identità. Questa è la lezione più costosa presente nel registro delle insidie del repository e il controllo `one_voice_per_character` serve a garantire che questa lezione venga appresa.
- **I valori numerici per il mix derivano da standard e studi sull'ascolto** (BS.1770-5, AES TD1008, ricerca sul ducking JAES), non da impressioni soggettive; sono delle manopole perché le preferenze differiscono in modo misurabile.
- **La governance è una funzionalità.** Non clonare la voce di una persona reale senza il suo consenso. Il discorso sintetico pubblicato nell'UE comporta un obbligo di marcatura leggibile dalla macchina ai sensi dell'articolo 50; il file JSON di ricevuta è progettato per far parte di tale traccia di provenienza e la [sezione sulla pubblicazione della Knowledge Base](docs/knowledge-base.md#publishing--governance-read-before-you-ship-a-dubbed-video) ti indica quali informazioni devi divulgare nel luogo in cui pubblichi. Non utilizzare pacchetti vocali specifici per persone, mai. Né per le chiamate automatiche.

## Stato

**v1.0.0: la pipeline è stata implementata e entrambe le ricevute sono positive.** Una scena notturna con due personaggi ottiene un punteggio di **19/19** nel contratto del contenitore (48 kHz, −18.09 LUFS, dialogo +11.17 LU rispetto al livello di riferimento, 161 fotogrammi intatti, 10.069 s) e **11/11** nel contratto dei contenuti. 167 test, CI positivo. Cronologia completa in [CHANGELOG](CHANGELOG.md).

| Elemento | Stato |
|---|---|
| [Handbook](https://mcp-tool-shop-org.github.io/fx-dub/handbook/) — installazione, utilizzo, script delle scene, generatori di grafici, verifica | ✅ |
| [Motivazioni del progetto](docs/design/2026-08-21-fxdub-v1.dispatch.md) — 45 risultati ottenuti alla base di ogni impostazione predefinita | ✅ citazioni verificate esternamente ([record](docs/design/2026-08-21-fxdub-v1.dispatch.verify.md), ricevuta Ed25519 nel repository) |
| [Knowledge Base](docs/knowledge-base.md) — ogni opzione, licenze trasparenti, costi misurati | ✅ |
| [Onboarding degli agenti](AGENTS.md) + database del progetto ([kb/fxdub.db](kb/README.md)) — nodi, modelli, esecuzioni, **65 insidie misurate**, decisioni | ✅ attivo; ricostruito a ogni sessione |
| Sequenza temporale degli eventi per effetti sonori · canale GPU locale | ⏳ tabella di marcia |

## Per agenti e LLM

Inizia con [AGENTS.md](AGENTS.md) — il manuale operativo definitivo — quindi consulta [HANDOFF.md](HANDOFF.md) per lo stato attuale, quindi interroga `kb/fxdub.db` per il registro delle insidie. Un riepilogo leggibile dalla macchina è pubblicato all'indirizzo [`/fx-dub/llms.txt`](https://mcp-tool-shop-org.github.io/fx-dub/llms.txt).

## Provenienza

Questo repository adotta un approccio di sviluppo basato sulle ricevute: i grafici vengono estratti dalla piattaforma e verificati (feed di fatturazione, intestazioni dell'output decodificate) anziché essere considerati affidabili sulla base dei report; le citazioni del progetto superano una verifica esterna da parte di un sistema diverso prima di diventare architettura; i numeri misurati contengono i loro UUID. Quando viene rilevata un'insidia, la stessa commit aggiunge il rilevatore, il seed del database e il test.

## Licenza

[MIT](LICENSE) — sia per il repository che per il pacchetto. I pesi dei modelli hanno le proprie licenze; la [Knowledge Base](docs/knowledge-base.md) è la mappa trasparente. © 2026 mcp-tool-shop.

<p align="center">
  Built by <a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a>
</p>
