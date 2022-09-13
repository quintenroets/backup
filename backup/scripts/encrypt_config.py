import cli
from plib import Path

filename = "rclone.conf.gpg"
src = Path.HOME / ".config" / "rclone" / filename
dst = Path(__file__).parent.parent.parent / "assets" / filename

unencrypted_src = src.with_suffix("")
cli.run(f"gpg --symmetric {unencrypted_src}")
src.rename(dst)
