"""TuonTa entry point."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

if sys.version_info < (3, 11):
    sys.exit("TuonTa needs Python 3.11 or newer.")

from TuonTa.ui.app import TuonTaApp  # noqa: E402


def main() -> None:
    TuonTaApp().mainloop()


if __name__ == "__main__":
    main()
