"""fx-dub — receipts for generated dubs.

Two verifiers, and the difference between them is the whole point:

* :mod:`fxdub.audition_receipt` checks the CONTAINER — sample rate, duration,
  EBU R128 loudness, dialogue-to-bed ducking depth, and whether the re-muxed
  MP4 actually carries an audio track with its frames intact.
* :mod:`fxdub.dialogue_receipt` checks what was actually SAID — every scripted
  line present and in order, no speech the script never asked for, no two
  characters talking over each other, no mid-line pause that eats the next
  cue, one voice per character.

A take can pass the first and be unusable. That is not hypothetical: it is why
the second one exists.

**Building on fx-dub? Import** :mod:`fxdub.verify` **and nothing else.** It is the
declared public API: the alignment core that answers "was this script actually
spoken", with the video-specific thresholds and checks left behind in
``dialogue_receipt`` where they belong. Everything outside ``verify`` is a console
script or an internal that may move between releases.
"""

__version__ = "1.2.0"

__all__ = ["__version__"]
