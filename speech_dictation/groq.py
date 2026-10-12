from . import messages
from . import net
from . import textproc
from . import usage
from .batch import BatchSession, wav

URL = "https://api.groq.com/openai/v1/audio/transcriptions"
MODELS = {
    "groq": "whisper-large-v3",
    "groq-turbo": "whisper-large-v3-turbo",
}
# Whisper reads at most 224 tokens of prompt; a short word list stays well inside it.
MAX_PROMPT = 600


class GroqSession(BatchSession):
    """Sends the recording to Groq Whisper once it ends."""

    missing_key = messages.GROQ_KEY_MISSING

    def __init__(self, api_key, model="groq", language="", trim=True, vocabulary=""):
        super().__init__(api_key, trim)
        self._model = MODELS.get(model, MODELS["groq"])
        self._language = (language or "").strip()
        self._words = textproc.words_of(vocabulary)

    def transcribe(self, pcm):
        fields = [("model", self._model), ("response_format", "json"), ("temperature", "0")]
        if self._language:
            fields.append(("language", self._language))
        if self._words:
            # Whisper takes the prompt as earlier text, so these spellings win.
            fields.append(("prompt", (", ".join(self._words) + ".")[:MAX_PROMPT]))
        body, content_type = net.multipart(fields, "speech.wav", "audio/wav", wav(pcm))
        data = net.post("groq", URL, body, content_type, {"Authorization": "Bearer " + self._key})
        usage.record("speech", self._model, seconds=len(pcm) / 32000)
        return (data.get("text") or "").strip()
