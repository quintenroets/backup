import cli

from backup.models import Path


def check_setup(*, install: bool = True) -> None:
    path = Path.rclone_config
    if not path.exists():
        download_config_file(path)
        if install:
            install_rclone()


def install_rclone() -> None:
    # curl required inside rclone install.sh script
    commands = (
        "sudo apt-get install -y curl",
        "curl https://rclone.org/install.sh | sudo bash",
    )
    cli.run_commands_in_shell(*commands, check=False)


def download_config_file(path: Path) -> None:
    file_id = "1apaAlz06Hm37AJLl3CNp3zQoofP7yJu4"
    url = f"https://docs.google.com/uc?export=download&id={file_id}"
    path.create_parent()
    cli.capture_output("wget --no-check-certificate", url, "-O", path)
