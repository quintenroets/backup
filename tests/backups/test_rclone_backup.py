from backup.backup.rclone import Rclone


def test_status() -> None:
    rclone = Rclone()
    rclone.run("version")
