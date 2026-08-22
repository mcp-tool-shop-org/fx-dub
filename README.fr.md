<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.md">English</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

**Vérifiez un doublage généré avant que quiconque ne l’entende.**

Votre modèle de synthèse vocale a renvoyé un son stéréo à 48 kHz avec la durée exacte et une valeur de -18 LUFS, comme indiqué dans les spécifications. Il a également prononcé une phrase que vous n’avez jamais écrite, avec une voix qui ne correspond pas à celle de votre personnage, et il y a un trou de deux secondes au milieu.

Aucun de ces éléments n’est visible lors de la vérification du taux d’échantillonnage et de la durée. fx-dub vous fournit deux rapports : un pour le fichier source et un pour ce qui a été réellement dit, et il renvoie une valeur différente de zéro si l’une ou l’autre des vérifications échoue.

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

Cet échec est bien réel. Un modèle en mode `audio reference` a reproduit les *dialogues* de son clip de référence, et pas seulement sa sonorité, ce qui signifie qu’un fichier audio destiné à contenir les répliques d’un personnage a refait entendre les répliques de l’autre. Mixé avec la prise originale, cela donne l’impression que deux personnes parlent en même temps. Taux d’échantillonnage : parfait. Durée : parfaite.

## Les deux rapports

| | Vérifications | Détecte les erreurs |
|---|---|---|
| **`fxdub-receipt`** | ensemble de fichiers à livrer, masters 48 kHz, niveau sonore EBU R128, profondeur d’atténuation du dialogue par rapport à la musique d’ambiance, fichier MP4 remixé contenant les **deux** pistes, images intactes | un doublage silencieux, un doublage tronqué, des dialogues noyés dans la musique d’ambiance, un mixage qui n’a pas atteint son objectif |
| **`fxdub-dialogue`** | toutes les répliques du scénario présentes et dans l’ordre, aucune phrase inventée, aucun chevauchement de personnages, aucune interruption au milieu d’une phrase, une voix par personnage, correspond au clip | un modèle qui invente des répliques, un personnage dont la voix change entre les rendus, une pause qui empiète sur la réplique suivante, deux personnages réduits à une seule voix |

**Une vérification échouée est une découverte, et non un bug dans l’outil.** Signalez-la ; ne modifiez jamais le seuil pour qu’elle soit validée. Chaque vérification fait référence à la norme ou au défaut mesuré auquel elle se réfère, afin que vous puissiez en discuter en vous basant sur des preuves.

## Le scénario est le contrat

La direction d’acteurs est présente dans le scénario, et non dans l’esprit du réalisateur :

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

`max_gap_s` pour cette ligne explique pourquoi le vérificateur rejette une prise qu’un seuil global laisserait passer. La note à côté indique pourquoi la valeur est de 0,15 et non d’une autre valeur.

`--only-speaker MAC` réduit le contrat à un seul personnage, ce qui permet de vérifier un **fichier audio par personnage** : il doit contenir les répliques de ce personnage et du *silence* lorsque c’est un autre personnage qui parle. La vérification d’un fichier audio par rapport à l’ensemble de la scène masque précisément le bug mentionné ci-dessus.

## Obtenir une transcription

`fxdub-dialogue` lit une transcription diaralisée au niveau du mot — `{text, start, end, speaker_id}` per word. Any diarizing ASR will do. `fxdub.vo_graphs.transcribe()` et crée le graphique ComfyUI pour un seul élément :

```python
from fxdub import vo_graphs

graph = vo_graphs.transcribe("<storage-key>.flac", "run/words")
# -> API-format dict, ready for your own submit path. Nothing is sent from here.
```

## Créateurs de graphiques

`fxdub.vo_graphs` crée également les graphiques de la phase VO : conception vocale, référence audio du même moteur, clonage et synthèse vocale, assemblage, placement sur la ligne temporelle, mixage. Ils existent parce que l’alternative — taper manuellement le JSON de l’API dans une fenêtre de chat — produit des graphiques qui disparaissent avec la session et réintroduisent silencieusement des défauts pour lesquels on a déjà payé.

Chaque créateur est vérifié par les détecteurs de pièges du dépôt, de sorte que les éléments qui entraînent de véritables échecs ne peuvent pas être recréés accidentellement. Voici deux exemples de ce que cela encode :

- L’entrée d’auto-extension du nœud clone d’ElevenLabs est adressée comme `files.audio0` au moment de l’exécution — et non le `files.item_1` annoncé dans son propre schéma — et une exécution à blanc accepte le nom incorrect sans se plaindre.
- Le `pitch_rate` de ByteDance est global pour chaque nœud, ce qui signifie qu’un seul nœud ne peut pas donner la voix à deux personnages avec des tonalités différentes. Ses horodatages font référence à une ligne temporelle de sortie absolue, de sorte que la solution consiste à effectuer un passage par personnage, en superposition.

La création d’un graphique est une fonction pure qui prend des arguments et renvoie un `dict`. **Rien dans ce package ne soumet, ne télécharge ou n’utilise.**

## Modèle de menace

fx-dub s’exécute localement et n’effectue aucun appel réseau.

- **Données concernées :** uniquement les fichiers que vous nommez dans la ligne de commande — masters FLAC/MP4, manifestes LUFS, texte des sous-titres, JSON de transcription. Il écrit un rapport à l’emplacement `--json` que vous choisissez.
- **Données non concernées :** aucun identifiant, aucune clé API, aucun secret d’environnement, aucun fichier en dehors des chemins que vous transmettez.
- **Autorisations requises :** lecture du système de fichiers pour les fichiers d’entrée ; écriture du système de fichiers uniquement si vous transmettez `--json`.
- **Sortie réseau : aucune.** Il n’y a pas de client HTTP ici et la liste des dépendances au moment de l’exécution est vide par conception — le CI fait échouer la compilation si cela change un jour.
- **Télémétrie : aucune.** Rien n’est collecté, comptabilisé ou transmis.

L’analyse des médias se limite aux bibliothèques standard : les flux FLAC `STREAMINFO` et les atomes MP4 sont décodés directement plutôt que d’utiliser une commande externe vers `ffprobe`. Une entrée malformée entraîne une vérification échouée, et non un plantage. Politique complète dans [SECURITY.md](SECURITY.md).

## Codes de sortie

| Code | Signification |
|---|---|
| `0` | toutes les vérifications ont réussi |
| `1` | l’audio n’a pas satisfait aux exigences du contrat — lisez le rapport |
| `2` | l’outil n’a pas pu s’exécuter — chemin incorrect, JSON malformé, locuteur inconnu |

`1` and `2` stay distinct on purpose: in CI the first wants its receipt read, the
second means the invocation is wrong. Errors print `{code, message, hint}` on
stderr; `--debug` re-raises instead.

## Le pipeline que ces rapports vérifient

fx-dub a commencé comme un pipeline de doublage natif ComfyUI et il en est toujours ainsi. Il s’exécute sur [Comfy Cloud](https://cloud.comfy.org) :

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

> **« Re-mux »** = re-multiplexer : la bande sonore finale est réintégrée dans le conteneur vidéo, les pixels restant intacts. Ce n’est pas une faute de frappe pour « remix », car le mixage a lieu à l’étape précédente ; il s’agit de l’étape qui vous fournit un `dubbed.mp4` que vous pouvez lire.

**Réglez le niveau sonore en fonction du compteur, et non en fonction des valeurs mémorisées.** Les moteurs diffèrent de 8 dB sur la même ligne : le remplacement d’un moteur TTS par un autre a fait passer une piste vocale de -18,34 à -25,03 LUFS. La réutilisation des paramètres fixes de la recette précédente aurait masqué les dialogues de 7 dB, alors que toutes les autres vérifications étaient validées.

## Ce qui est honnête dans cette conception

- **Les légendes apportent du sens, pas une synchronisation temporelle.** Un processus basé sur les légendes est de qualité ambiante et dialogue ; il ne synchronisera jamais le bruit d’une porte claquant uniquement par le biais d’un texte. Une synchronisation de haute qualité nécessite une chronologie des événements — la [Base de connaissances](docs/knowledge-base.md#stage-2b--direct-videoaudio-the-sync-first-alternative) répertorie les modèles vidéo→audio directs qui le font nativement, ainsi que leurs licences.
- **Une description de scène n’est pas un scénario.** Vous écrivez les mots que vos personnages prononcent ; le processus permet de les rendre naturels.
- **L’identité vocale n’est pas gratuite.** Les voix conçues à l’aide d’invites sont non déterministes, *quels que soient les paramètres* — une voix que vous approuvez ne peut pas être rappelée en relançant la même invite. Définissez une fois, conservez l’audio approuvé, puis référencez-le ou insérez-le indéfiniment. Le clonage inter-moteurs ne préserve pas non plus l’identité. C’est la leçon la plus coûteuse du registre des pièges de ce dépôt, et la vérification `one_voice_per_character` permet de s’assurer qu’elle est retenue.
- **Les valeurs numériques correspondent aux normes et aux études d’écoute** (BS.1770-5, AES TD1008, recherches sur le « ducking » de JAES), et non à des impressions subjectives — et ce sont des réglages, car les préférences diffèrent de manière mesurable.
- **La gouvernance est une fonctionnalité.** Ne clonez pas la voix d’une personne réelle sans son consentement. Les discours synthétiques publiés dans l’UE sont soumis à une obligation de marquage lisible par machine en vertu de l’article 50 ; le fichier JSON de réception est conçu pour faire partie de cette chaîne de traçabilité, et la [section sur la publication de la base de connaissances](docs/knowledge-base.md#publishing--governance-read-before-you-ship-a-dubbed-video) vous indique quelles informations vous devez divulguer en fonction du lieu où vous publiez. Pas d’ensembles de voix spécifiques à une personne, jamais. Pas pour les appels automatisés.

## État

**v1.0.0 — le processus est livré et les deux accusés de réception sont positifs.** Une scène nocturne avec deux personnages obtient un score de **19/19** sur le contrat du conteneur (48 kHz, −18,09 LUFS, dialogue +11,17 LU par rapport à la base, 161 images intactes, 10,069 s) et un score de **11/11** sur le contrat du contenu. 167 tests, CI positif. Historique complet dans le [JOURNAL DES MODIFICATIONS](CHANGELOG.md).

| Élément | État |
|---|---|
| [Manuel](https://mcp-tool-shop-org.github.io/fx-dub/handbook/) — installation, utilisation, scripts de scène, créateurs de graphiques, vérification | ✅ |
| [Justification de la conception](docs/design/2026-08-21-fxdub-v1.dispatch.md) — 45 conclusions étayées pour chaque valeur par défaut | ✅ citations vérifiées en externe ([enregistrement](docs/design/2026-08-21-fxdub-v1.dispatch.verify.md), accusé de réception Ed25519 dans le dépôt) |
| [Base de connaissances](docs/knowledge-base.md) — toutes les options, licences honnêtes, coûts mesurés | ✅ |
| [Intégration des agents](AGENTS.md) + base de données du projet ([kb/fxdub.db](kb/README.md)) — nœuds, modèles, exécutions, **65 pièges mesurés**, décisions | ✅ en direct ; reconstruit à chaque session |
| Chronologie des événements pour les effets sonores ponctuels · canal GPU local | ⏳ feuille de route |

## Pour les agents et les LLM

Commencez par [AGENTS.md](AGENTS.md) — le manuel d’utilisation durable — puis [HANDOFF.md](HANDOFF.md) pour l’état en direct, puis interrogez `kb/fxdub.db` pour obtenir le registre des pièges. Un résumé lisible par machine est publié à l’adresse [`/fx-dub/llms.txt`](https://mcp-tool-shop-org.github.io/fx-dub/llms.txt).

## Traçabilité

Ce dépôt applique une approche de développement axée sur les accusés de réception : les graphiques sont extraits de la plateforme et vérifiés (flux de facturation, en-têtes de sortie décodés) plutôt que de se fier aux rapports ; les citations de conception passent un vérificateur externe différent avant de devenir une architecture ; les valeurs mesurées portent leurs UUID d’exécution. Lorsqu’un piège est détecté, la même validation ajoute le détecteur, la base de données et le test.

## Licence

[MIT](LICENSE) — pour le dépôt et le paquet. Les poids des modèles sont soumis à leurs propres licences ; la [Base de connaissances](docs/knowledge-base.md) est la carte honnête. © 2026 mcp-tool-shop.

<p align="center">
  Built by <a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a>
</p>
