from speech_dictation.certs import install as _install_certs
from speech_dictation.crashlog import install as _install_crashlog

_install_certs()
_install_crashlog()

from speech_dictation.__main__ import main

if __name__ == "__main__":
    main()
