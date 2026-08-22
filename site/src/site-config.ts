import type { SiteConfig } from '@mcptoolshop/site-theme';

export const config: SiteConfig = {
  title: 'fx-dub',
  description:
    'Verify a generated dub before anyone hears it — container receipts and spoken-content receipts for AI dialogue pipelines.',
  logoBadge: 'FX',
  brandName: 'fx-dub',
  repoUrl: 'https://github.com/mcp-tool-shop-org/fx-dub',
  footerText:
    'MIT Licensed — built by <a href="https://github.com/mcp-tool-shop-org" style="color:var(--color-muted);text-decoration:underline">mcp-tool-shop-org</a>',

  hero: {
    badge: 'Open source · zero dependencies',
    headline: 'Your dub passed every check',
    headlineAccent: 'and still said the wrong line.',
    description:
      '48 kHz, exact duration, textbook −18 LUFS — and a line you never wrote, in a voice that is not your character’s, with a two-second hole in the middle. fx-dub gives you two receipts: one for the container, one for what was actually said.',
    primaryCta: { href: '#usage', label: 'Get started' },
    secondaryCta: { href: 'handbook/', label: 'Read the Handbook' },
    previews: [
      { label: 'Install', code: 'pip install fx-dub' },
      {
        label: 'Check the content',
        code: 'fxdub-dialogue scene.json words.json --only-speaker VOICE',
      },
      {
        label: 'Check the container',
        code: 'fxdub-receipt runs/2026-08-22-final --json receipt.json',
      },
    ],
  },

  sections: [
    {
      kind: 'features',
      id: 'features',
      title: 'Two receipts, because one is not enough',
      subtitle:
        'Sample rate and duration cannot see a model inventing dialogue. Both of the takes that made this tool necessary passed every container check.',
      features: [
        {
          title: 'Content, not just container',
          desc: 'Every scripted line present and in order, no invented speech, no cross-character overlap, no mid-line pause that eats the next cue, one voice per character.',
        },
        {
          title: 'The scene script is the contract',
          desc: 'Dialogue, cast, clip duration and per-line delivery direction live as data. A director’s phrasing note travels with the number it justifies.',
        },
        {
          title: 'Per-character stems',
          desc: '--only-speaker narrows the contract to one character, so a stem is checked for their lines and silence everywhere else. Checking against the whole scene hides exactly that bug.',
        },
        {
          title: 'Standards, not vibes',
          desc: 'EBU R128 loudness, ATSC A/85 dialogue anchoring, JAES ducking-depth research. Every check cites the standard or the measured defect it traces to.',
        },
        {
          title: 'No network, no dependencies',
          desc: 'Zero runtime dependencies and no HTTP client — CI fails the build if that ever changes. FLAC and MP4 headers are decoded with the standard library, not by shelling out to ffprobe.',
        },
        {
          title: 'Exit codes CI can act on',
          desc: '0 pass · 1 the audio failed its contract, read the receipt · 2 the tool could not run. Errors carry code, message and hint — never a raw traceback.',
        },
      ],
    },
    {
      kind: 'code-cards',
      id: 'usage',
      title: 'Usage',
      cards: [
        {
          title: 'Install',
          code: 'pip install fx-dub',
        },
        {
          title: 'Check what a take actually says',
          code: '$ fxdub-dialogue docs/scenes/night-street.json words.json --only-speaker VOICE\n9/10 checks pass\n| PASS | line_present:0:VOICE    | Hey, how’s it going?\n| FAIL | no_invented_speech      | 4 unscripted word(s): not bad can’t complain\n| PASS | no_overlap              | clean\n| PASS | one_voice_per_character | clean',
        },
        {
          title: 'A scene script',
          code: '{\n  "clip_duration_s": 10.062,\n  "lines": [\n    { "speaker": "VOICE", "text": "Hey, how’s it going?" },\n    { "speaker": "MAC",   "text": "Not bad. Can’t complain.",\n      "max_gap_s": 0.15,\n      "direction": "There’s no pause in between." },\n    { "speaker": "VOICE", "text": "Good to hear, good to hear." }\n  ]\n}',
        },
        {
          title: 'Check the delivered run',
          code: '$ fxdub-receipt runs/2026-08-22-v28 --bed-gain-db -12\n19/19 checks passed.\n| PASS | loudness:mix_target       | -18.09 LUFS (target -18.0 +/- 2.0)\n| PASS | loudness:dialogue_anchored| VO - bed = +11.17 LU (expect 8-20)\n| PASS | dub:frames_intact         | 161 frames',
        },
        {
          title: 'Build a graph without submitting it',
          code: 'from fxdub import vo_graphs\n\ngraph = vo_graphs.transcribe("<storage-key>.flac", "run/words")\n# API-format dict, ready for your own submit path.\n# Nothing is sent, uploaded, or spent from here.',
        },
      ],
    },
  ],
};
