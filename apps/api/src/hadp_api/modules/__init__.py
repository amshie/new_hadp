"""Domain modules (business capabilities).

Importing this package registers every ORM model on `Base.metadata`, which Alembic
relies on for migration autogeneration. Modules expose public application services;
they must not reach into another module's repositories or tables directly.
"""

from hadp_api.modules.audit import models as audit_models  # noqa: F401
from hadp_api.modules.consents import models as consent_models  # noqa: F401
from hadp_api.modules.derivations import models as derivation_models  # noqa: F401
from hadp_api.modules.documents import models as document_models  # noqa: F401
from hadp_api.modules.identity import models as identity_models  # noqa: F401
from hadp_api.modules.imports import models as import_models  # noqa: F401
from hadp_api.modules.interpretation import models as interpretation_models  # noqa: F401
from hadp_api.modules.kpi import models as kpi_models  # noqa: F401
from hadp_api.modules.observations import models as observation_models  # noqa: F401
from hadp_api.modules.patients import models as patient_models  # noqa: F401
from hadp_api.modules.reports import models as report_models  # noqa: F401
from hadp_api.modules.tenancy import models as tenancy_models  # noqa: F401
