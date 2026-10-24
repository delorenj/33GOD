# Speech fixture

`speech.wav` is real synthesized speech, produced locally with eSpeak NG (the
same real CPU engine used through Vox). It is NOT a tone, silence, recording
from production, or a mocked transcript. Text: "The voice pipeline is working."
The smoke asserts only a nonempty transcript without error, not exact wording.
Regenerate using `espeak-ng --stdout -v en-us -s 150` then reframe WAV sizes;
`runtime/espeak_engine.py` contains the identical procedure.
