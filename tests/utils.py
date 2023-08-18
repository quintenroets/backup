from hypothesis import HealthCheck, settings

ignore_fixture_warning = settings(
    suppress_health_check=(HealthCheck.function_scoped_fixture,)
)
