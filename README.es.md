<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.md">English</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

**Verifica un doblaje generado antes de que alguien lo escuche.**

Tu modelo de conversión de texto a voz devolvió audio estéreo de 48 kHz con la duración exacta y un nivel de -18 LUFS, tal como se indica en los manuales. También dijo una línea que nunca escribiste, con una voz que no es la de tu personaje, y con un silencio de dos segundos en el medio.

Ninguno de estos problemas es visible al analizar la frecuencia de muestreo y la duración. fx-dub te proporciona dos informes: uno para el archivo y otro para **lo que realmente se dijo**, y sale con un código de error diferente de cero si alguno falla.

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

Este fallo es real. Un modelo en modo `audio reference` reprodujo el *diálogo* del clip de referencia, no solo su timbre; por lo tanto, una pista destinada a contener las líneas de un personaje reproduce silenciosamente las líneas del otro. Mezclado con la grabación original, suena como si dos personas estuvieran hablando al mismo tiempo. Frecuencia de muestreo: perfecta. Duración: perfecta.

## Los dos informes

| | Comprobaciones | Detecta errores |
|---|---|---|
| **`fxdub-receipt`** | conjunto de archivos entregables, masters de 48 kHz, sonoridad EBU R128, profundidad de atenuación del diálogo con respecto a la música de fondo, el archivo MP4 remultiplexado contiene **ambas** pistas y los fotogramas están intactos. | un doblaje silencioso, un doblaje truncado, el diálogo se escucha muy bajo en relación con la música de fondo, una mezcla que no cumple con su objetivo |
| **`fxdub-dialogue`** | todas las líneas del guion presentes y en orden, sin diálogos inventados, sin superposición entre personajes, sin interrupciones a mitad de línea, una voz por personaje, se ajusta al clip | un modelo que inventa líneas, un personaje cuya voz cambia entre renderizaciones, una pausa que elimina la siguiente indicación, dos personajes combinados en una sola voz |

**Una comprobación fallida es un hallazgo, no un error en la herramienta.** Infórmalo; nunca ajustes el umbral para que aparezca como correcto. Cada comprobación cita el estándar o el defecto medido al que hace referencia, para que puedas discutirlo basándote en las pruebas.

## El guion de la escena es el contrato

La dirección se encuentra en el guion, no en la mente del agente:

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

`max_gap_s` en esa línea explica por qué el verificador rechaza una toma que un umbral global permitiría. La nota al lado indica por qué el número es 0,15 y no otro.

`--only-speaker MAC` limita el contrato a un personaje, que es la forma de comprobar una **pista por personaje**: debe contener las líneas de ese personaje y *silencio* cuando hable cualquier otra persona. Comprobar una pista con toda la escena oculta exactamente el error mencionado anteriormente.

## Obtener una transcripción

`fxdub-dialogue` lee una transcripción diarizada a nivel de palabra: `{text, start, end, speaker_id}` per word. Any diarizing ASR will do. `fxdub.vo_graphs.transcribe()` y construye el gráfico de ComfyUI para la misma:

```python
from fxdub import vo_graphs

graph = vo_graphs.transcribe("<storage-key>.flac", "run/words")
# -> API-format dict, ready for your own submit path. Nothing is sent from here.
```

## Constructores de gráficos

`fxdub.vo_graphs` también construye los gráficos de la etapa VO: diseño de voz, referencia de audio del mismo motor, clonación y síntesis de voz, empalme, colocación en la línea de tiempo, mezcla. Existen porque la alternativa (escribir manualmente el JSON de la API en una ventana de chat) produce gráficos que desaparecen con la sesión y reintroducen silenciosamente los defectos por los que ya se ha pagado.

Cada constructor es validado por los detectores de errores del repositorio, por lo que las formas que causan fallos reales no pueden ser creadas accidentalmente. Dos ejemplos de lo que esto codifica:

- La entrada de crecimiento automático del nodo de clonación de ElevenLabs se aborda como `files.audio0` en tiempo de ejecución —**no** el `files.item_1` que anuncia su propio esquema— y una prueba preliminar acepta el nombre incorrecto sin quejarse.
- El parámetro `pitch_rate` de ByteDance es global para el nodo, por lo que un nodo no puede dar voz a dos personajes con diferentes tonos. Sus marcas de tiempo se refieren a una línea de tiempo de salida absoluta, por lo que la solución es un paso por personaje, en capas.

Construir un gráfico es una función pura que toma argumentos y devuelve un `dict`. **Nada en este paquete envía, carga ni gasta.**

## Modelo de amenazas

fx-dub se ejecuta localmente y no realiza ninguna llamada de red.

- **Datos accedidos:** solo los archivos que especificas en la línea de comandos: masters FLAC/MP4, manifiestos LUFS, texto de subtítulos, JSON de transcripción. Escribe un informe en la ruta `--json` que elijas.
- **Datos NO accedidos:** ninguna credencial, ninguna clave de API, ningún secreto del entorno, ningún archivo fuera de las rutas que proporcionas.
- **Permisos requeridos:** lectura del sistema de archivos para los archivos de entrada; escritura del sistema de archivos solo si pasas `--json`.
- **Salida de red: ninguna.** No hay cliente HTTP aquí y la lista de dependencias en tiempo de ejecución está vacía por diseño; el CI falla la compilación si esto alguna vez cambia.
- **Telemetría: ninguna.** No se recopila, cuenta ni transmite nada.

El análisis multimedia solo utiliza bibliotecas estándar: los archivos FLAC `STREAMINFO` y los átomos MP4 se decodifican directamente en lugar de utilizar comandos externos `ffprobe`. Los archivos de entrada incorrectos generan una comprobación fallida, no un error. Política completa en [SECURITY.md](SECURITY.md).

## Códigos de salida

| Código | Significado |
|---|---|
| `0` | todas las comprobaciones superadas |
| `1` | el audio no cumplió con el contrato; lee el informe |
| `2` | la herramienta no pudo ejecutarse: ruta incorrecta, JSON mal formado, hablante desconocido |

`1` and `2` stay distinct on purpose: in CI the first wants its receipt read, the
second means the invocation is wrong. Errors print `{code, message, hint}` on
stderr; `--debug` re-raises instead.

## La secuencia de comandos que verifican estos informes

fx-dub comenzó como una secuencia de comandos de doblaje nativa de ComfyUI y sigue siéndolo. Se ejecuta en [Comfy Cloud](https://cloud.comfy.org):

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

> **"Remultiplexar"** = volver a multiplexar: la banda sonora final se vuelve a escribir en el archivo de vídeo, sin modificar los píxeles. No es un error tipográfico para "remezclar"; la mezcla se realiza una etapa antes; este es el paso que te proporciona un `dubbed.mp4` reproducible.

**Ajusta el nivel desde el medidor, nunca a partir de números memorizados.** Los motores difieren en 8 dB en la misma línea: cambiar un TTS por otro movió una pista de voz de -18,34 a -25,03 LUFS. Reutilizar la ganancia fija de la receta anterior habría atenuado el diálogo en 7 dB, mientras que todas las demás comprobaciones seguían siendo correctas.

## Lo bueno de este diseño

- **Los subtítulos transmiten significado, no tiempo.** Un flujo de trabajo basado en subtítulos es adecuado para ambientes y diálogos; nunca sincronizará el sonido de una puerta cerrándose solo con texto. Para lograr un impacto significativo, se necesita una línea de tiempo de eventos: la [Base de conocimientos](docs/knowledge-base.md#stage-2b--direct-videoaudio-the-sync-first-alternative) muestra los modelos directos de video a audio que lo hacen de forma nativa, y sus licencias.
- **Una descripción de una escena no es un guion.** Usted escribe las palabras que dicen sus personajes; el flujo de trabajo se encarga de que suenen bien.
- **La identidad vocal no es gratuita.** Las voces diseñadas a partir de indicaciones no son deterministas, *independientemente de la semilla* — una voz que aprueba no puede recuperarse volviendo a ejecutar la misma indicación. Elija las voces una vez, conserve el audio aprobado y luego utilícelo o incorpórelo indefinidamente. La clonación entre diferentes motores tampoco preserva la identidad. Esta es la lección más costosa en el registro de trampas del repositorio, y la verificación `one_voice_per_character` es lo que garantiza que se aprenda.
- **Los valores numéricos para la mezcla provienen de estándares y estudios de audición** (BS.1770-5, AES TD1008, investigación sobre atenuación de JAES), no de sensaciones — y son controles, porque las preferencias difieren de manera medible.
- **La gobernanza es una característica.** No clone la voz de una persona real sin su consentimiento. El discurso sintético publicado en la UE conlleva una obligación de marcado legible por máquina según el Artículo 50; el archivo JSON de recibo está diseñado para formar parte de ese registro de procedencia, y la [sección de publicación de la Base de conocimientos](docs/knowledge-base.md#publishing--governance-read-before-you-ship-a-dubbed-video) le indica qué divulgación debe realizar en el lugar donde publique. No se permiten paquetes de voces específicas para personas, nunca. Ni siquiera para llamadas automatizadas.

## Estado

**v1.0.0: el flujo de trabajo está implementado y ambos recibos son positivos.** Una escena nocturna con dos personajes obtiene una puntuación de **19/19** en el contrato del contenedor (48 kHz, −18.09 LUFS, diálogo +11.17 LU sobre la base, 161 fotogramas intactos, 10.069 s) y **11/11** en el contrato de contenido. 167 pruebas, CI positivo. Historial completo en [CHANGELOG](CHANGELOG.md).

| Elemento | Estado |
|---|---|
| [Manual](https://mcp-tool-shop-org.github.io/fx-dub/handbook/) — instalación, uso, guiones de escenas, generadores de gráficos, verificación | ✅ |
| [Justificación del diseño](docs/design/2026-08-21-fxdub-v1.dispatch.md) — 45 hallazgos documentados que respaldan cada valor predeterminado | ✅ citas verificadas externamente ([registro](docs/design/2026-08-21-fxdub-v1.dispatch.verify.md), recibo Ed25519 en el repositorio) |
| [Base de conocimientos](docs/knowledge-base.md) — todas las opciones, licencias honestas, costos medidos | ✅ |
| [Incorporación de agentes](AGENTS.md) + base de datos del proyecto ([kb/fxdub.db](kb/README.md)) — nodos, modelos, ejecuciones, **65 trampas medidas**, decisiones | ✅ activo; reconstruido en cada sesión |
| Línea de tiempo de eventos de efectos de sonido · canal local-GPU | ⏳ hoja de ruta |

## Para agentes y LLM

Comience en [AGENTS.md](AGENTS.md) — el manual operativo duradero — luego, consulte [HANDOFF.md](HANDOFF.md) para conocer el estado actual y, a continuación, consulte `kb/fxdub.db` para obtener el registro de trampas. Se publica un resumen legible por máquina en [`/fx-dub/llms.txt`](https://mcp-tool-shop-org.github.io/fx-dub/llms.txt).

## Procedencia

Este repositorio aplica el desarrollo basado en recibos: los gráficos se extraen de la plataforma y se verifican (flujo de facturación, encabezados de salida decodificados) en lugar de confiar en informes; las citas del diseño pasan por un verificador externo diferente antes de convertirse en arquitectura; los números medidos llevan sus UUID de trabajo. Cuando se encuentra una trampa, la misma confirmación agrega el detector, la semilla de la base de datos y la prueba.

## Licencia

[MIT](LICENSE) — tanto para el repositorio como para el paquete. Los pesos del modelo tienen sus propias licencias; la [Base de conocimientos](docs/knowledge-base.md) es el mapa honesto. © 2026 mcp-tool-shop.

<p align="center">
  Built by <a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a>
</p>
