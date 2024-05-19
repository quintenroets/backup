from functools import cached_property

from package_utils.context import Context as Context_

from ..models import Config, Options, Secrets
from ..storage.storage import Storage


class Context(Context_[Options, Config, Secrets]):
    @cached_property
    def storage(self) -> Storage:
        return Storage()


context = Context(Options, Config, Secrets)
