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
"""

__version__ = "1.0.1"

__all__ = ["__version__"]
