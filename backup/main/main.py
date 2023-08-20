import cli

from ..backups import Backup
from ..utils import Path, get_args


def main():
    args = get_args()

    if args.configure:
        cli.urlopen(Path.config)
    else:
        backup = Backup(include_browser=args.include_browser)
        match args.action:
            case "status":
                backup.status()
            case "push":
                backup.push()
            case "pull":
                backup.sync_remote = not args.no_sync
                backup.sub_check = args.subcheck
                backup.pull()


if __name__ == "__main__":
    main()
