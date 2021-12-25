from ..base import ActionValidationBase, ValidationException
from ...enums import RepositoryFile


class IntegrationManifest(ActionValidationBase, category="integration"):
    def check(self):
        if RepositoryFile.MAINIFEST_JSON not in [x.filename for x in self.repository.tree]:
            raise ValidationException(
                f"The repository has no '{RepositoryFile.MAINIFEST_JSON}' file"
            )
