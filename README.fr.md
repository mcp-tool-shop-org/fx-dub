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

Votre modèle de synthèse vocale a renvoyé un signal stéréo à 48 kHz avec la durée exacte et une valeur LUFS de -18, conforme aux normes. Il a également prononcé une phrase que vous n’avez jamais écrite, avec une voix qui ne correspond pas à celle de votre personnage, et il y a un trou de deux secondes au milieu.

Aucun de ces éléments n’est visible lors de l’analyse du taux d’échantillonnage et de la durée. fx-dub vous fournit deux rapports : un pour le fichier audio et un pour **ce qui a été réellement dit**, et renvoie une valeur différente de zéro si l’une ou l’autre des vérifications échoue.

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

Cet échec est bien réel. Un modèle en mode `audio reference` a reproduit le *dialogue* de son clip de référence, et pas seulement sa sonorité ; ainsi, une piste audio censée contenir les répliques d’un personnage a refait entendre les répliques de l’autre. Mixé avec la prise originale, cela donne l’impression que deux personnes parlent en même temps. Taux d’échantillonnage : parfait. Durée : parfaite.

## Les deux rapports

| | Vérifications | Détection des erreurs |
|---|---|---|
| **`fxdub-receipt`** | ensemble de fichiers à livrer, masters à 48 kHz, niveau sonore EBU R128, profondeur d’atténuation du dialogue par rapport à la musique d’ambiance, fichier MP4 remixé contenant **les deux** pistes audio, images intactes, **nombre de personnes dans le sous-titre comparé au casting**. | doublage silencieux, doublage tronqué, dialogues noyés dans la musique d’ambiance, mixage qui n’atteint pas son objectif, **un créateur de sous-titres ajoutant une personne à la scène**. |
| **`fxdub-dialogue`** | toutes les répliques du scénario présentes et dans l’ordre, aucune phrase inventée, aucun chevauchement entre les personnages, aucune interruption au milieu d’une réplique, une voix par personnage, correspond au clip. | un modèle qui invente des répliques, un personnage dont le rôle change entre les rendus, une pause qui empiète sur la réplique suivante, deux personnages réduits à une seule voix. |

**Une vérification échouée est une découverte, et non un bug dans l’outil.** Signalez-la ; ne modifiez jamais le seuil pour qu’elle soit validée. Chaque vérification fait référence à la norme ou au défaut mesuré auquel elle se réfère, afin que vous puissiez en discuter en vous basant sur des preuves.

## Le scénario est le contrat

La direction d’acteurs est présente dans le scénario, et non dans l’esprit du réalisateur :

```json
{
  "clip_duration_s": 10.062,
  "cast": {
    "VOICE": { "description": "off-frame, deep and gritty", "on_frame": false },
    "MAC":   { "description": "on-frame, gritty, weary", "on_frame": true,
               "face": { "frame": 60, "x": 348, "y": 122 } }
  },
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

`on_frame` permet à un fichier sans informations visuelles de détecter un défaut dans les sous-titres. Passez `--scene` à `fxdub-receipt` et il compare le nombre de personnes que le sous-titre *indique* au nombre de personnes que le contrat déclare être visibles. Pour la version livrée, cette vérification échoue : le créateur de sous-titres a écrit « deux hommes… face à face » sur une scène où il n’y a qu’un seul homme, et c’est ce sous-titre qui alimente l’invite audio.

`--only-speaker MAC` réduit le contrat à un seul personnage, ce qui permet de vérifier une **piste audio par personnage** : elle doit contenir les répliques de ce personnage et du *silence* lorsque c’est un autre personnage qui parle. Vérifier une piste par rapport à l’ensemble de la scène masque précisément le bug mentionné ci-dessus.

## Obtenir une transcription

`fxdub-dialogue` lit une transcription diaralisée au niveau du mot — `{text, start, end, speaker_id}` per word. Any diarizing ASR will do. `fxdub.vo_graphs.transcribe()` et construit le graphique ComfyUI pour cela :

```python
from fxdub import vo_graphs

graph = vo_graphs.transcribe("<storage-key>.flac", "run/words")
# -> API-format dict, ready for your own submit path. Nothing is sent from here.
```

## L’API publique — `fxdub.verify`

**Nouveauté dans la version 1.2.0.** Les deux scripts de console vérifient un *doublage vidéo*. Le moteur sous-jacent — qui compare un script à ce qui a été réellement dit — n’est pas spécifique à la vidéo, et il est exporté en tant qu’interface déclarée et stable, afin que d’autres outils puissent s’y appuyer au lieu d’importer des éléments internes qui pourraient être modifiés.

```python
from fxdub import verify

lines = [{"speaker": "narrator", "text": "Chapter two continues the tale."}]
result = verify.align_lines(lines, words)      # words: the transcript above

result.missing            # scripted lines that were never spoken
result.invented_words     # rendered tokens no scripted line claimed

verify.check_all_lines_present(result)   # -> Check(name, ok, detail, traces_to)
verify.check_no_invented_speech(result)
verify.check_one_voice_per_line(result)
```

Ces trois éléments s’appliquent à n’importe quel processus qui transforme un texte écrit en parole synthétisée : **une ligne demandée par le script doit être prononcée, une ligne qu’il n’a pas demandée ne doit pas l’être, et un personnage doit être interprété par une seule voix, la sienne.** Ils ont été testés par rapport à une deuxième base de code avant d’être déclarés : quatre défauts de contenu détectés dans un moteur de rendu EPUB vers livre audio (une note de bas de page narrée, un chapitre supprimé lors d’un rendu partiel et signalé comme une réussite, trois personnages réduits à une seule voix, un balisage lu à haute voix comme du texte) sont désormais intégrés dans [`tests/test_verify.py`](tests/test_verify.py), à côté d’un contrôle de référence qui ne doit rien signaler.

Ce qui n’est **pas** inclus dans l’API : la transcription (fx-dub utilise les moments où les mots sont prononcés, c’est pourquoi il n’a aucune dépendance), les seuils (chacun d’eux est lié à un défaut détecté à l’oreille dans un média donné, ils appartiennent donc à l’appelant qui gère la politique) et les vérifications spécifiques au média : chevauchement, décalage en milieu de ligne, ajustement de la séquence, profondeur de l’atténuation, légende par rapport au doublage. Une vérification qui ne peut pas être effectuée de manière significative dans votre média est pire que l’absence de vérification, car elle est interprétée comme une réussite.

`fxdub-dialogue` est lui-même un consommateur de cette API : il calcule ses verdicts de contenu via `verify` et n’ajoute que ce qui fait d’un reçu un reçu de *doublage*. Cela est appliqué par des tests qui font échouer `verify` et exigent que l’interface en ligne de commande échoue également, de sorte que le chemin public ne puisse pas devenir silencieusement un chemin que personne n’utilise.

## Créateurs de graphiques

`fxdub.vo_graphs` crée également les graphiques pour l’étape du doublage : conception vocale, référence audio avec le même moteur, clonage et synthèse vocale, assemblage, insertion dans la chronologie, mixage, ainsi que l’étape de l’image : extraction d’images, synchronisation labiale et multiplexage. Ils existent parce que l’alternative — taper manuellement du JSON API dans une fenêtre de chat — produit des graphiques qui disparaissent avec la session et réintroduisent silencieusement des défauts pour lesquels on a déjà payé.

Chaque créateur est vérifié par les détecteurs de pièges du dépôt, de sorte que les configurations qui entraînent de véritables échecs ne peuvent pas être recréées accidentellement. Voici deux exemples de ce que cela encode :

- L’entrée à croissance automatique du nœud de clonage ElevenLabs est adressée comme `files.audio0` au moment de l’exécution — et non `files.item_1`, comme indiqué dans son propre schéma —, et une exécution à blanc accepte le nom incorrect sans se plaindre.
- Le `pitch_rate` de ByteDance est global pour tous les nœuds, de sorte qu’un seul nœud ne peut pas donner la voix à deux personnages avec des tonalités différentes. Ses horodatages font référence à une chronologie de sortie absolue, de sorte que la solution consiste à effectuer un passage par personnage, en superposition.
- L’entrée `speaker_selection` du nœud de synchronisation labiale a par défaut « laissez le modèle décider ». Si vous ne la fixez pas, l’exécution se termine, renvoie un fichier MP4 correctement encadré avec la bonne durée et valide toutes les vérifications du conteneur, mais c’est la bouche de la mauvaise personne qui bouge. Le créateur fixe les coordonnées ; le détecteur rejette le graphique qui ne le fait pas.

La création d’un graphique est une fonction pure qui prend des arguments et renvoie un `dict`. **Rien dans ce paquet ne soumet, ne télécharge ou n’utilise.**

## Modèle de menace

fx-dub s’exécute localement et n’effectue aucun appel réseau.

- **Données traitées :** uniquement les fichiers que vous nommez dans la ligne de commande — masters FLAC/MP4, manifestes LUFS, texte des sous-titres, JSON de transcription. Il écrit un rapport à l’emplacement `--json` que vous choisissez.
- **Données NON traitées :** aucun identifiant, aucune clé API, aucun secret d’environnement, aucun fichier en dehors des chemins que vous transmettez.
- **Autorisations requises :** lecture du système de fichiers pour les fichiers d’entrée ; écriture du système de fichiers uniquement si vous passez `--json`.
- **Sortie réseau : aucune.** Il n’y a pas de client HTTP ici et la liste des dépendances au moment de l’exécution est vide par conception — CI fait échouer la construction si cela change un jour.
- **Télémétrie : aucune.** Rien n’est collecté, comptabilisé ou transmis.

L’analyse des médias se limite aux bibliothèques standard : les flux FLAC `STREAMINFO` et les atomes MP4 sont décodés directement plutôt que d’utiliser une commande externe vers `ffprobe`. Les fichiers d’entrée malformés entraînent un échec de la vérification, et non un plantage. Politique complète dans [SECURITY.md](SECURITY.md).

## Codes de sortie

| Code | Signification |
|---|---|
| `0` | toutes les vérifications ont réussi |
| `1` | l’audio n’a pas satisfait son contrat — lisez le rapport |
| `2` | l’outil n’a pas pu s’exécuter — chemin incorrect, JSON malformé, locuteur inconnu |

`1` and `2` stay distinct on purpose: in CI the first wants its receipt read, the
second means the invocation is wrong. Errors print `{code, message, hint}` on
stderr; `--debug` re-raises instead.

## Le pipeline qui valide ces données de vérification

fx-dub a commencé comme un pipeline de doublage natif ComfyUI et en est toujours un. Il fonctionne sur :
[Comfy Cloud](https://cloud.comfy.org) :

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
                                   │
                       (optional)  ▼
                    lip-sync ─► sync one named face to that
                                character's own track, then
                                re-mux the full mix back over it
```

> **« Re-mux »** = re-multiplexage : la bande sonore finale est réintégrée dans le
> conteneur vidéo, les pixels restant intacts. Ce n’est pas une faute de frappe pour « remix », car le mixage a lieu
> à l’étape précédente ; c’est cette étape qui vous fournit un fichier `dubbed.mp4` lisible.

**Réglez le niveau d’amplification à partir du compteur, et non en vous fiant à des valeurs mémorisées.** Les moteurs diffèrent de
8 dB sur la même ligne : remplacer un TTS par un autre a fait passer une piste vocale de −18,34 à
−25,03 LUFS. Réutiliser le gain fixe de la recette précédente aurait étouffé les
dialogues de 7 dB, alors que tous les autres contrôles restaient verts.

## Qu’est-ce qui justifie cette conception ?

- **Les sous-titres véhiculent un sens, et non une synchronisation.** Un pipeline basé sur des sous-titres est adapté aux ambiances
et aux dialogues ; il ne synchronisera jamais le bruit d’une porte qui claque uniquement à l’aide de descriptions textuelles. Une
synchronisation de qualité nécessite une chronologie des événements : la
[base de connaissances](docs/knowledge-base.md#stage-2b--direct-videoaudio-the-sync-first-alternative)
associe les modèles vidéo→audio directs qui le font nativement, ainsi que leurs licences.
- **Une description de scène n’est pas un scénario.** Vous écrivez les mots que vos personnages prononcent ;
le pipeline se charge de leur donner une sonorité appropriée.
- **L’identité vocale n’est pas gratuite.** Les voix conçues à l’aide d’invites sont non déterministes,
*quel que soit le nombre aléatoire* : une voix que vous approuvez ne peut pas être rappelée en relançant la même invite. Choisissez-la une fois, conservez l’enregistrement audio approuvé, puis référencez-le ou insérez-le de manière permanente. La duplication entre différents moteurs ne préserve pas non plus l’identité. C’est
la leçon la plus coûteuse du registre des pièges du dépôt, et le contrôle `one_voice_per_character` du vérificateur permet de s’assurer qu’elle est retenue.
- **La synchronisation labiale commande un visage, elle a donc besoin d’une piste pour un seul personnage.** Fournissez-lui le mixage
et il fera bouger les lèvres de chaque réplique, y compris celles qui appartiennent à une personne qui n’est pas
dans le plan, tout en passant tous les contrôles audio, car l’audio n’a pas changé.
Fournissez-lui une piste par personnage et le silence deviendra la performance correcte :
le personnage écoute. Les résultats sont non déterministes *quel que soit le nombre aléatoire*, de sorte qu’une prise approuvée est conservée et jamais réinterprétée. Le nœud recalcule également le timing de l’image ;
vérifiez le nombre d’images du produit final, et non de sa sortie brute.
- **Les valeurs numériques du mixage proviennent des normes et des études d’écoute** (BS.1770-5,
AES TD1008, recherches sur l’atténuation JAES), et non de simples impressions ; ce sont des boutons, car
les préférences diffèrent de manière mesurable.
- **La gouvernance est une fonctionnalité.** Ne clonez pas la voix d’une personne réelle sans son consentement.
Les discours synthétiques publiés dans l’UE sont soumis à une obligation de marquage lisible par machine en vertu de l’article 50 ; le fichier JSON des données de vérification est conçu pour faire partie de cette chaîne de traçabilité, et la
[section sur la publication de la base de connaissances](docs/knowledge-base.md#publishing--governance-read-before-you-ship-a-dubbed-video)
vous indique quelles informations vous devez divulguer en fonction du lieu où vous publiez. Pas de packs vocaux spécifiques à une personne, jamais. Pas pour les appels automatisés.

## État

**Version 1.2.0 : le processus est livré, les deux reçus sont valides, l’image est synchronisée avec les lèvres, et le moteur d’alignement est désormais une API publique déclarée.** Une scène nocturne avec deux personnages obtient un score de **19/19** sur le contrat du conteneur (48 kHz, −18,09 LUFS, dialogue +11,17 LU par rapport à la base, 161 images intactes, 10,069 s) et de **11/11** sur le contrat du contenu. La variante synchronisée avec les lèvres conserve le même contrat : 832 × 480, 161 images, les deux pistes, avec la bouche de MAC sur sa ligne et fermée pendant que le personnage hors cadre parle.

Elle obtient un score de **19/20** une fois que vous passez `--scene`, et l’échec est réel : la légende de l’exécution fournie indique deux hommes dans une scène où il n’y a qu’un seul personnage. Cette vérification a détecté un défaut qui était passé inaperçu. **277 tests**, CI valide. Historique complet dans le [CHANGELOG](CHANGELOG.md).

Cette version ajoute [`fxdub.verify`](#the-public-api--fxdubverify) : l’interface déclarée et indépendante du média sur laquelle d’autres outils peuvent s’appuyer, et elle corrige deux défauts que rien dans la suite de tests n’a pu détecter : un reçu enregistré contenant le chemin absolu de la machine qui l’a créé, et un déclencheur CI qui exécutait la matrice complète deux fois à chaque publication. Les deux ont désormais des détecteurs, chacun ayant été testé et s’étant avéré invalide par rapport aux données réelles avant la correction.

| Élément | État |
|---|---|
| [Manuel](https://mcp-tool-shop-org.github.io/fx-dub/handbook/) : installation, utilisation, scripts de scène, générateurs de graphiques, vérification | ✅ |
| [Justification de la conception](docs/design/2026-08-21-fxdub-v1.dispatch.md) : 45 éléments documentés qui justifient chaque valeur par défaut | ✅ citations vérifiées en externe ([enregistrement](docs/design/2026-08-21-fxdub-v1.dispatch.verify.md), reçu Ed25519 dans le dépôt) |
| [Base de connaissances](docs/knowledge-base.md) : toutes les options, licences honnêtes, coûts mesurés | ✅ |
| [Intégration d’agents](AGENTS.md) + base de données du projet ([kb/fxdub.db](kb/README.md)) : nœuds, modèles, exécutions, **86 pièges mesurés**, décisions | ✅ en direct ; reconstruit à chaque session |
| Chronologie des événements d’effets sonores ponctuels · ligne GPU locale | ⏳ feuille de route |

## Pour les agents et les LLM

Commencez par [AGENTS.md](AGENTS.md) : le manuel d’utilisation durable, puis
[HANDOFF.md](HANDOFF.md) pour l’état en direct, puis interrogez `kb/fxdub.db` pour obtenir le registre des pièges. Un résumé lisible par machine est publié à l’adresse
[`/fx-dub/llms.txt`](https://mcp-tool-shop-org.github.io/fx-dub/llms.txt).

## Traçabilité

Ce dépôt applique une approche de développement axée sur les données de vérification : les graphiques sont extraits de la plateforme
et validés (flux de facturation, en-têtes de sortie décodés) plutôt que d’être considérés comme fiables à partir des rapports ; les citations de conception passent un vérificateur externe différent avant de devenir une architecture ; les valeurs numériques portent leurs UUID d’exécution. Lorsqu’un piège est détecté,
la même validation ajoute le détecteur, la base de données et le test.

## Licence

[MIT](LICENSE) : le dépôt et le package. Les poids des modèles sont soumis à leurs propres licences ;
la [base de connaissances](docs/knowledge-base.md) est la carte honnête. © 2026 mcp-tool-shop.

<p align="center">
  Built by <a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a>
</p>
