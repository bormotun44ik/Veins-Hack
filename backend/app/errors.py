class VeinsError(Exception):
    code: str = "INTERNAL_ERROR"
    http_status: int = 500

class PersonNotFound(VeinsError):
    code = "PERSON_NOT_FOUND"
    http_status = 404
    def __init__(self, person_id: str):
        self.person_id = person_id
        super().__init__(f"Person not found: {person_id}")

class BadLayer(VeinsError):
    code = "BAD_LAYER"
    http_status = 400

class LLMUnavailable(VeinsError):
    code = "LLM_UNAVAILABLE"
    http_status = 503

class BadEvent(VeinsError):
    code = "BAD_EVENT"
    http_status = 400
