from .path import Path


class ActiveProfile:
    @property
    def name(self):
        return Path.active_profile.text.strip() or "light"

    @name.setter
    def name(self, name):
        Path.active_profile.text = name


active_profile = ActiveProfile()
