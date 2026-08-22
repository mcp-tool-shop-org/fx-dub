<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.md">English</a>
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

**Verifique uma versão dublada antes que alguém a ouça.**

Seu modelo de conversão de texto em fala retornou áudio estéreo de 48 kHz com a duração exata e um nível de loudness de -18 LUFS, conforme o padrão. Ele também reproduziu uma frase que você nunca escreveu, com uma voz diferente da do personagem, com uma pausa de dois segundos no meio.

Nenhuma dessas informações é visível na análise da taxa de amostragem e duração. O fx-dub fornece duas confirmações: uma para o arquivo e outra para **o que foi realmente dito**; ele retorna um código de erro diferente de zero se alguma das verificações falhar.

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

Essa falha é real. Um modelo no modo `audio reference` reproduziu o *diálogo* do clipe de referência, não apenas seu timbre — portanto, uma faixa destinada a conter as falas de um personagem reproduziu silenciosamente as falas do outro. Misturado com a gravação original, soou como se duas pessoas estivessem falando ao mesmo tempo. Taxa de amostragem: perfeita. Duração: perfeita.

## As duas confirmações

| | Verificações | Problemas detectados |
|---|---|---|
| **`fxdub-receipt`** | conjunto de arquivos final, masters de 48 kHz, loudness EBU R128, profundidade de redução do volume do diálogo em relação à trilha sonora, arquivo MP4 remixado que contém **ambas** as faixas, quadros intactos | uma versão dublada silenciosa, uma versão dublada truncada, diálogo abafado na trilha sonora, uma mixagem que não atingiu o objetivo |
| **`fxdub-dialogue`** | todas as falas do roteiro presentes e na ordem correta, nenhuma fala inventada, nenhum cruzamento de personagens, nenhuma pausa no meio da frase, uma voz por personagem, compatível com o clipe | um modelo inventando falas, um personagem sendo redefinido entre as renderizações, uma pausa que interrompe a próxima fala, dois personagens combinados em uma única voz |

**Uma verificação com falha é uma constatação, não um erro na ferramenta.** Relate-a; nunca ajuste o limite para que ela seja aprovada. Cada verificação cita o padrão ou o defeito medido ao qual se refere, para que você possa discutir os resultados com base nas evidências.

## O roteiro da cena é o contrato

A direção está no roteiro, não na mente de um agente:

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

`max_gap_s` nessa linha explica por que o verificador rejeita uma gravação, enquanto um limite global permitiria a passagem. A nota ao lado indica por que o número é 0,15 e não outro valor.

`--only-speaker MAC` restringe o contrato a um personagem, que é como você verifica uma **faixa por personagem**: ela deve conter as falas desse personagem e *silêncio* quando qualquer outra pessoa fala. Verificar uma faixa em relação à cena inteira oculta exatamente o erro mencionado acima.

## Obtendo uma transcrição

`fxdub-dialogue` lê uma transcrição diarizada no nível da palavra — `{text, start, end, speaker_id}` per word. Any diarizing ASR will do. `fxdub.vo_graphs.transcribe()` e constrói o gráfico do ComfyUI para ela:

```python
from fxdub import vo_graphs

graph = vo_graphs.transcribe("<storage-key>.flac", "run/words")
# -> API-format dict, ready for your own submit path. Nothing is sent from here.
```

## Construtores de gráficos

`fxdub.vo_graphs` também constrói os gráficos da fase VO: design de voz, referência de áudio com o mesmo mecanismo, clonagem e reprodução, emenda, inserção na linha do tempo, mixagem. Eles existem porque a alternativa — digitar manualmente o JSON da API em uma janela de chat — produz gráficos que desaparecem com a sessão e reintroduzem silenciosamente defeitos pelos quais já se pagou.

Cada construtor é verificado pelos detectores de erros do repositório, para que as configurações que causam falhas reais não possam ser criadas acidentalmente. Dois exemplos do que isso codifica:

- A entrada de autoexpansão do nó de clonagem da ElevenLabs é tratada como `files.audio0` em tempo de execução — **não** o `files.item_1` que seu próprio esquema anuncia — e uma execução de teste aceita o nome incorreto sem reclamação.
- O `pitch_rate` da ByteDance é global para o nó, portanto, um único nó não pode dar voz a dois personagens com tons diferentes. Seus carimbos de data/hora se referem a uma linha do tempo de saída absoluta, portanto, a correção é uma passagem por personagem, em camadas.

Construir um gráfico é uma função pura que recebe argumentos e retorna um `dict`. **Nada neste pacote envia, carrega ou gasta.**

## Modelo de ameaças

O fx-dub é executado localmente e não faz chamadas de rede de qualquer tipo.

- **Dados acessados:** apenas os arquivos que você especifica na linha de comando — masters FLAC/MP4, manifestos LUFS, texto da legenda, JSON da transcrição. Ele grava uma confirmação no caminho `--json` que você escolher.
- **Dados NÃO acessados:** nenhuma credencial, nenhuma chave de API, nenhum segredo de ambiente, nenhum arquivo fora dos caminhos que você fornecer.
- **Permissões necessárias:** leitura do sistema de arquivos nos arquivos de entrada; gravação no sistema de arquivos somente se você fornecer `--json`.
- **Saída de rede: nenhuma.** Não há cliente HTTP aqui e a lista de dependências em tempo de execução está vazia por design — o CI falha na compilação se isso mudar.
- **Telemetria: nenhuma.** Nada é coletado, contado ou transmitido.

A análise de mídia usa apenas bibliotecas padrão: os átomos FLAC `STREAMINFO` e MP4 são decodificados diretamente, em vez de usar comandos externos `ffprobe`. Uma entrada malformada resulta em uma verificação com falha, não em uma falha. Política completa em [SECURITY.md](SECURITY.md).

## Códigos de saída

| Código | Significado |
|---|---|
| `0` | todas as verificações foram aprovadas |
| `1` | o áudio não atendeu ao contrato — leia a confirmação |
| `2` | a ferramenta não pôde ser executada — caminho inválido, JSON malformado, alto-falante desconhecido |

`1` and `2` stay distinct on purpose: in CI the first wants its receipt read, the
second means the invocation is wrong. Errors print `{code, message, hint}` on
stderr; `--debug` re-raises instead.

## O pipeline que essas confirmações verificam

O fx-dub começou como um pipeline de dublagem nativo do ComfyUI e ainda é um. Ele é executado no [Comfy Cloud](https://cloud.comfy.org):

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

> **"Remixar"** = re-multiplexar: a trilha sonora final é gravada de volta no contêiner de vídeo, sem alterar os pixels. Não é um erro de digitação para "mixar" — a mixagem ocorre em uma etapa anterior; esta é a etapa que fornece um arquivo `dubbed.mp4` reproduzível.

**Ajuste o ganho com base no medidor, nunca com base em números memorizados.** Os mecanismos diferem em 8 dB na mesma linha: substituir um TTS por outro moveu uma faixa de voz de -18,34 para -25,03 LUFS. Reutilizar o ganho fixo da receita anterior teria abafado o diálogo em 7 dB, enquanto todas as outras verificações permaneceriam aprovadas.

## O que é honesto neste design

- **As legendas transmitem significado, não tempo.** Um fluxo de trabalho mediado por legendas é adequado para ambientes e diálogos; nunca sincronizará o som de uma porta batendo apenas com texto. A sincronização precisa requer uma linha do tempo de eventos — a [Base de Conhecimento](docs/knowledge-base.md#stage-2b--direct-videoaudio-the-sync-first-alternative) mapeia os modelos diretos de vídeo→áudio que o fazem nativamente, e suas licenças.
- **Uma descrição de cena não é um roteiro.** Você escreve as palavras que seus personagens dizem; o fluxo de trabalho faz com que soem corretas.
- **A identidade da voz não é gratuita.** As vozes projetadas por prompts são não determinísticas *independentemente da semente* — uma voz que você aprova não pode ser recuperada executando o mesmo prompt novamente. Defina uma vez, mantenha o áudio aprovado e, em seguida, faça referência ou combine-o para sempre. A clonagem entre mecanismos também não preserva a identidade. Esta é a lição mais cara no registro de armadilhas do repositório, e a verificação `one_voice_per_character` garante que ela seja aprendida.
- **Os níveis de mixagem vêm de padrões e estudos de audição** (BS.1770-5, AES TD1008, pesquisa de ducking JAES), não de impressões — e são controles, porque as preferências diferem mensuravelmente.
- **A governança é um recurso.** Não clone a voz de uma pessoa real sem consentimento. A fala sintética publicada na UE acarreta uma obrigação de marcação legível por máquina do Artigo 50; o recibo JSON é construído para fazer parte desse registro de origem, e a [seção de publicação da Base de Conhecimento](docs/knowledge-base.md#publishing--governance-read-before-you-ship-a-dubbed-video) informa qual divulgação você deve fornecer onde publicar. Sem pacotes de voz específicos para pessoas, nunca. Nem para chamadas automatizadas.

## Status

**v1.0.0 — o fluxo de trabalho é entregue e ambos os recibos estão positivos.** Uma cena noturna com dois personagens obtém **19/19** no contrato do contêiner (48 kHz, −18,09 LUFS, diálogo +11,17 LU acima da base, 161 quadros intactos, 10,069 s) e **11/11** no contrato de conteúdo. 167 testes, CI positivo. Histórico completo em [CHANGELOG](CHANGELOG.md).

| Parte | Estado |
|---|---|
| [Manual](https://mcp-tool-shop-org.github.io/fx-dub/handbook/) — instalação, uso, roteiros de cena, criadores de gráficos, verificação | ✅ |
| [Justificativa do projeto](docs/design/2026-08-21-fxdub-v1.dispatch.md) — 45 descobertas documentadas por trás de cada padrão | ✅ citações verificadas externamente ([registro](docs/design/2026-08-21-fxdub-v1.dispatch.verify.md), recibo Ed25519 no repositório) |
| [Base de Conhecimento](docs/knowledge-base.md) — todas as opções, licenças honestas, custos mensurados | ✅ |
| [Integração de agentes](AGENTS.md) + banco de dados do projeto ([kb/fxdub.db](kb/README.md)) — nós, modelos, execuções, **65 armadilhas mensuradas**, decisões | ✅ ativo; reconstruído a cada sessão |
| Linha do tempo de eventos de efeitos sonoros · canal GPU local | ⏳ roteiro |

## Para agentes e LLMs

Comece em [AGENTS.md](AGENTS.md) — o manual operacional duradouro — depois, [HANDOFF.md](HANDOFF.md) para o estado ativo e, em seguida, consulte `kb/fxdub.db` para o registro de armadilhas. Um resumo legível por máquina é publicado em [`/fx-dub/llms.txt`](https://mcp-tool-shop-org.github.io/fx-dub/llms.txt).

## Rastreabilidade

Este repositório pratica o desenvolvimento com recibos primeiro: os gráficos são extraídos da plataforma e verificados (feed de faturamento, cabeçalhos de saída decodificados) em vez de serem confiáveis a partir de relatórios; as citações de projeto passam por um verificador externo diferente antes de se tornarem arquitetura; os números mensurados carregam seus UUIDs de trabalho. Quando uma armadilha é encontrada, o mesmo commit adiciona o detector, a semente do banco de dados e o teste.

## Licença

[MIT](LICENSE) — o repositório e o pacote. Os pesos do modelo carregam suas próprias licenças; a [Base de Conhecimento](docs/knowledge-base.md) é o mapa honesto. © 2026 mcp-tool-shop.

<p align="center">
  Built by <a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a>
</p>
