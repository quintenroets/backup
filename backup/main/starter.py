import argparse
from dataclasses import dataclass, field

import cli

from ..backups import Backup
from ..utils import Action, Path, get_args


@dataclass
class Starter:
    args: argparse.Namespace = field(default_factory=get_args)

    def start(self):
        if self.args.configure:
            cli.urlopen(Path.config)
        else:
            sub_check_path = self.get_sub_check_path()
            paths = [Path(path) for path in self.args.items]
            backup = Backup(
                include_browser=self.args.include_browser,
                sub_check_path=sub_check_path,
                paths=paths,
                show_diff=self.args.show_diff,
            )
            self.run_backup(backup)

    def get_sub_check_path(self):
        if self.args.export_resume:
            sub_check_path = Path.resume
        elif self.args.subcheck:
            sub_check_path = Path.cwd()
        else:
            sub_check_path = None
        if sub_check_path is not None:
            sub_check_path = sub_check_path.relative_to(Backup.source)
        return sub_check_path

    def run_backup(self, backup: Backup):
        if self.args.export_resume:
            self.args.action = Action.pull
        match self.args.action:
            case Action.status:
                backup.status()
            case Action.push:
                backup.push()
            case Action.pull:
                backup.sync_remote = not self.args.no_sync
                backup.pull()
            case Action.diff:
                backup.diff(diff_all=self.args.all)
