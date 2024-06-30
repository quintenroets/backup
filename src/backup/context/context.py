from package_utils.context import Context

from backup.models import Config, Options, Secrets

context = Context(Options, Config, Secrets)
